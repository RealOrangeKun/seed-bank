"""``/api/v1/traffic-splits`` — admin-only A/B routing knobs.

GET lists active splits.
PATCH replaces the splits for a single ``(kind, seed_type_id)`` segment
atomically: in one transaction we deactivate any existing rows and insert
the new ones. Weights must sum to ≤100 (the schema's CHECK on a single
row is per-row; the sum check is a service-layer rule).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select

from seedbank.api.deps import DbSession, RedisDep, require_role
from seedbank.core.exceptions import ConflictError, NotFoundError, ValidationError
from seedbank.core.logging import get_logger
from seedbank.domain.user import AuthenticatedUser, Role
from seedbank.infrastructure.db.enums import ModelKind, ModelStatus
from seedbank.infrastructure.db.models import AuditLog, ModelArtifact, TrafficSplit
from seedbank.infrastructure.db.repositories import ModelArtifactRepository
from seedbank.schemas.model import TrafficSplitOut, TrafficSplitReplaceIn
from seedbank.services.traffic_router import TrafficRouter

log = get_logger(__name__)

router = APIRouter(prefix="/traffic-splits", tags=["traffic-splits"])

AdminUser = Annotated[AuthenticatedUser, Depends(require_role(Role.ADMIN))]


@router.get("", response_model=list[TrafficSplitOut])
async def list_splits(
    session: DbSession,
    _admin: AdminUser,
    kind: ModelKind | None = Query(default=None),
    seed_type_id: UUID | None = Query(default=None),
) -> list[TrafficSplitOut]:
    stmt = select(TrafficSplit).where(TrafficSplit.is_active.is_(True))
    if kind is not None:
        stmt = stmt.where(TrafficSplit.kind == kind.value)
    if seed_type_id is not None:
        stmt = stmt.where(TrafficSplit.seed_type_id == seed_type_id)
    stmt = stmt.order_by(TrafficSplit.kind, TrafficSplit.seed_type_id, TrafficSplit.created_at)
    rows = list((await session.execute(stmt)).scalars().all())
    return [TrafficSplitOut.model_validate(r) for r in rows]


@router.patch("", response_model=list[TrafficSplitOut])
async def replace_splits(
    payload: TrafficSplitReplaceIn,
    request: Request,
    session: DbSession,
    redis: RedisDep,
    actor: AdminUser,
) -> list[TrafficSplitOut]:
    """Atomically replace the traffic splits for one segment."""
    total = sum(e.weight for e in payload.entries)
    if total > 100:
        raise ValidationError(f"weights sum to {total}; must be ≤ 100.")

    # Verify every referenced model exists and is in a routable state.
    referenced_ids = [e.model_id for e in payload.entries]
    if referenced_ids:
        stmt = select(ModelArtifact).where(ModelArtifact.id.in_(referenced_ids))
        rows = {r.id: r for r in (await session.execute(stmt)).scalars().all()}
        for mid in referenced_ids:
            row = rows.get(mid)
            if row is None:
                raise NotFoundError(f"Model {mid} not found.")
            if row.status not in {
                ModelStatus.STAGING.value,
                ModelStatus.PRODUCTION.value,
            }:
                raise ValidationError(
                    f"Model {mid} status is {row.status}; "
                    "only staging/production may receive traffic."
                )
            if row.kind != payload.kind.value:
                raise ConflictError(
                    f"Model {mid} kind={row.kind} does not match split kind={payload.kind.value}."
                )

    # Hard-delete (rather than is_active=false) so the table doesn't accrue
    # stale audit-only rows; the audit_log row below records the change.
    seed_filter = (
        TrafficSplit.seed_type_id.is_(None)
        if payload.seed_type_id is None
        else TrafficSplit.seed_type_id == payload.seed_type_id
    )
    existing_stmt = select(TrafficSplit).where(
        TrafficSplit.kind == payload.kind.value, seed_filter
    )
    for old in (await session.execute(existing_stmt)).scalars().all():
        await session.delete(old)

    new_rows: list[TrafficSplit] = []
    for entry in payload.entries:
        new_row = TrafficSplit(
            kind=payload.kind.value,
            seed_type_id=payload.seed_type_id,
            model_id=entry.model_id,
            weight=entry.weight,
            is_active=True,
            valid_from=entry.valid_from,
            valid_until=entry.valid_until,
        )
        session.add(new_row)
        new_rows.append(new_row)

    session.add(
        AuditLog(
            actor_id=actor.id,
            action="traffic_splits.replace",
            target_type="traffic_split",
            target_id=f"{payload.kind.value}:{payload.seed_type_id or 'none'}",
            audit_metadata={
                "kind": payload.kind.value,
                "seed_type_id": str(payload.seed_type_id) if payload.seed_type_id else None,
                "entries": [
                    {"model_id": str(e.model_id), "weight": e.weight}
                    for e in payload.entries
                ],
                "total": total,
            },
            ip=request.client.host if request.client else None,
        )
    )

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    # Bust the router cache for this segment so requests pick up the change
    # within the next request cycle.
    tr = TrafficRouter(
        session=session, models=ModelArtifactRepository(session), redis=redis
    )
    await tr.invalidate(payload.kind, payload.seed_type_id)

    log.info(
        "traffic_splits.replaced",
        kind=payload.kind.value,
        seed_type_id=str(payload.seed_type_id) if payload.seed_type_id else None,
        total=total,
        n=len(new_rows),
    )
    for r in new_rows:
        await session.refresh(r)
    return [TrafficSplitOut.model_validate(r) for r in new_rows]


__all__ = ["router"]
