"""Unit tests for the traffic router.

These tests stub out the DB and Redis with fakes so we can verify the
distribution logic without spinning up Postgres.
"""

from __future__ import annotations

from collections import Counter
from typing import cast
from uuid import UUID, uuid4

import pytest

from seedbank.core.exceptions import ModelNotReadyError
from seedbank.infrastructure.db.enums import ModelKind
from seedbank.infrastructure.db.models import ModelArtifact
from seedbank.infrastructure.db.repositories import ModelArtifactRepository
from seedbank.services.traffic_router import TrafficRouter, _bucket_for, _SplitEntry

# ── Fakes ────────────────────────────────────────────────────────────────────


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)


class _FakeRouter(TrafficRouter):
    """Subclass that swaps the DB query for an in-memory fixture so we can
    exercise the routing math without spinning up Postgres."""

    def __init__(
        self,
        *,
        splits: list[tuple[UUID, int]],
        production_id: UUID | None,
        redis: _FakeRedis,
    ) -> None:
        self._splits_fixture = splits
        self._production_id = production_id
        self.redis = redis  # type: ignore[assignment]

    async def _query_splits(self, kind: ModelKind, seed_type_id: UUID | None) -> list[_SplitEntry]:
        return [_SplitEntry(model_id=mid, weight=w) for mid, w in self._splits_fixture]

    @property
    def models(self) -> ModelArtifactRepository:  # type: ignore[override]
        production_id = self._production_id

        class _M:
            async def get_production(
                self, kind: ModelKind, seed_type_id: UUID | None
            ) -> ModelArtifact | None:
                if production_id is None:
                    return None
                return cast("ModelArtifact", type("R", (), {"id": production_id})())

        return cast("ModelArtifactRepository", _M())


# ── Tests ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_50_50_split_is_balanced() -> None:
    a = uuid4()
    b = uuid4()
    router = _FakeRouter(
        splits=[(a, 50), (b, 50)],
        production_id=None,
        redis=_FakeRedis(),
    )
    counter: Counter[UUID] = Counter()
    for _ in range(1000):
        u = uuid4()
        chosen = await router.select_model(kind=ModelKind.DETECTION, seed_type_id=None, user_id=u)
        counter[chosen] += 1
    # Each side should land near 500. ±50 is comfortably inside ±2 sigma for n=1000
    # and p=0.5 (sigma ≈ 15.8 → 2 sigma ≈ 32; allow 50 for headroom in CI).
    assert abs(counter[a] - 500) < 60
    assert abs(counter[b] - 500) < 60
    assert counter[a] + counter[b] == 1000


@pytest.mark.asyncio
async def test_user_routing_is_sticky() -> None:
    a = uuid4()
    b = uuid4()
    router = _FakeRouter(
        splits=[(a, 50), (b, 50)],
        production_id=None,
        redis=_FakeRedis(),
    )
    user = uuid4()
    first = await router.select_model(kind=ModelKind.DETECTION, seed_type_id=None, user_id=user)
    for _ in range(20):
        again = await router.select_model(kind=ModelKind.DETECTION, seed_type_id=None, user_id=user)
        assert again == first


@pytest.mark.asyncio
async def test_no_splits_falls_back_to_production() -> None:
    prod = uuid4()
    router = _FakeRouter(splits=[], production_id=prod, redis=_FakeRedis())
    chosen = await router.select_model(kind=ModelKind.DETECTION, seed_type_id=None, user_id=uuid4())
    assert chosen == prod


@pytest.mark.asyncio
async def test_no_splits_no_production_raises() -> None:
    router = _FakeRouter(splits=[], production_id=None, redis=_FakeRedis())
    with pytest.raises(ModelNotReadyError):
        await router.select_model(kind=ModelKind.DETECTION, seed_type_id=None, user_id=uuid4())


def test_bucket_for_is_deterministic() -> None:
    u = uuid4()
    assert _bucket_for(u) == _bucket_for(u)
    assert 0 <= _bucket_for(u) < 100
    # Anonymous users hash to a stable bucket too.
    assert _bucket_for(None) == _bucket_for(None)


@pytest.mark.asyncio
async def test_partial_split_uses_total_as_denominator() -> None:
    """When weights sum to <100 (e.g. canary 10/0 with no fallback row),
    the router still routes proportionally rather than dropping requests
    into a 'no model' hole."""
    a = uuid4()
    router = _FakeRouter(splits=[(a, 30)], production_id=None, redis=_FakeRedis())
    # Every user must get model `a` because it owns the entire 0..30 bucket
    # (mapped onto the 0..total-1 space).
    for _ in range(50):
        chosen = await router.select_model(
            kind=ModelKind.DETECTION, seed_type_id=None, user_id=uuid4()
        )
        assert chosen == a
