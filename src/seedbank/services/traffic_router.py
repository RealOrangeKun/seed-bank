"""TrafficRouter — picks a model for ``(kind, seed_type_id)`` per request.

Algorithm
---------
* Read the active rows from ``traffic_splits`` for the segment.
* If they sum to 100, route by ``hash(user_id) % 100``: stable per user
  (sticky A/B) and uniform across the user space.
* If the table is empty for the segment, fall back to the production
  ``model_artifacts`` row.
* If neither, raise ``ModelNotReadyError`` — the API surfaces it as 503.

A short-lived Redis cache (60 s) holds the splits per segment so the hot
path doesn't hammer Postgres. Cache is invalidated by writes via the
``/traffic-splits`` endpoint.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.core.exceptions import ModelNotReadyError
from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.enums import ModelKind, ModelStatus
from seedbank.infrastructure.db.models import ModelArtifact, TrafficSplit
from seedbank.infrastructure.db.repositories import ModelArtifactRepository

log = get_logger(__name__)


_CACHE_TTL_SECONDS = 60


@dataclass(frozen=True, slots=True)
class _SplitEntry:
    model_id: UUID
    weight: int


def _segment_key(kind: ModelKind, seed_type_id: UUID | None) -> str:
    return f"traffic_splits:{kind.value}:{seed_type_id or 'none'}"


def _bucket_for(user_id: UUID | None) -> int:
    """Stable bucket in [0, 99]. Anonymous users get hashed by their None."""
    raw = str(user_id) if user_id is not None else "anonymous"
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    # Use the first 8 bytes as an unsigned int — plenty of entropy for mod 100.
    return int.from_bytes(digest[:8], "big") % 100


class TrafficRouter:
    def __init__(
        self,
        *,
        session: AsyncSession,
        models: ModelArtifactRepository,
        redis: Redis,
    ) -> None:
        self.session = session
        self.models = models
        self.redis = redis

    # ── Public API ───────────────────────────────────────────────────────────

    async def select_model(
        self,
        *,
        kind: ModelKind,
        seed_type_id: UUID | None,
        user_id: UUID | None,
    ) -> UUID:
        splits = await self._splits_for(kind, seed_type_id)
        if splits:
            total = sum(s.weight for s in splits)
            if total > 0:
                bucket = _bucket_for(user_id)
                cumulative = 0
                # Iterate in deterministic order (already sorted on read) so
                # the same user lands in the same model across requests.
                for entry in splits:
                    cumulative += entry.weight
                    # Map the bucket onto a 0..total-1 space when total<100,
                    # otherwise stick to the natural 0..99 mapping.
                    if total >= 100:
                        if bucket < cumulative:
                            return entry.model_id
                    else:
                        if bucket * total // 100 < cumulative:
                            return entry.model_id
                # Defensive fallback: last entry wins (rounding rounding).
                return splits[-1].model_id

        # No active splits → use the production row.
        prod = await self.models.get_production(kind, seed_type_id)
        if prod is not None:
            return prod.id

        raise ModelNotReadyError(
            f"No production model and no traffic splits for kind={kind.value} "
            f"seed_type_id={seed_type_id}"
        )

    async def invalidate(self, kind: ModelKind, seed_type_id: UUID | None) -> None:
        """Drop the cached splits for a segment after a write."""
        await self.redis.delete(_segment_key(kind, seed_type_id))

    # ── Internals ────────────────────────────────────────────────────────────

    async def _splits_for(self, kind: ModelKind, seed_type_id: UUID | None) -> list[_SplitEntry]:
        key = _segment_key(kind, seed_type_id)
        cached = await self.redis.get(key)
        if cached:
            try:
                payload = json.loads(cached)
                return [
                    _SplitEntry(model_id=UUID(item["model_id"]), weight=int(item["weight"]))
                    for item in payload
                ]
            except (ValueError, KeyError, TypeError):
                # Corrupt cache — fall through and refresh.
                pass

        rows = await self._query_splits(kind, seed_type_id)
        await self.redis.set(
            key,
            json.dumps([{"model_id": str(r.model_id), "weight": r.weight} for r in rows]),
            ex=_CACHE_TTL_SECONDS,
        )
        return rows

    async def _query_splits(self, kind: ModelKind, seed_type_id: UUID | None) -> list[_SplitEntry]:
        seed_filter = (
            TrafficSplit.seed_type_id.is_(None)
            if seed_type_id is None
            else TrafficSplit.seed_type_id == seed_type_id
        )
        now = datetime.now(tz=timezone.utc)
        stmt = (
            select(TrafficSplit)
            .where(
                TrafficSplit.kind == kind.value,
                seed_filter,
                TrafficSplit.is_active.is_(True),
            )
            .order_by(TrafficSplit.created_at, TrafficSplit.id)
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        live: list[_SplitEntry] = []
        for r in rows:
            if r.valid_from is not None and r.valid_from > now:
                continue
            if r.valid_until is not None and r.valid_until <= now:
                continue
            live.append(_SplitEntry(model_id=r.model_id, weight=int(r.weight)))
        return live


__all__ = ["TrafficRouter"]
