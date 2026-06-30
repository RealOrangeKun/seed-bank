"""``/api/v1/models`` — model registry HTTP endpoints.

Routers parse → call service → return. No SQLAlchemy here.
RBAC: ``ai_developer`` (and admins implicitly) can list/register/promote;
end users get 403.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from seedbank.api.deps import (
    ClickHouseDep,
    DbSession,
    ModelMetricRepoDep,
    StorageDep,
    require_role,
)
from seedbank.core.exceptions import ExternalServiceError
from seedbank.domain.user import AuthenticatedUser, Role
from seedbank.infrastructure.db.enums import ModelKind, ModelStatus
from seedbank.infrastructure.db.repositories import ModelArtifactRepository
from seedbank.schemas.common import Envelope, Page, paginate
from seedbank.schemas.model import (
    ModelOut,
    ModelPerformanceOut,
    ModelRegisterIn,
    ModelStatusUpdateIn,
    OfflineMetricOut,
)
from seedbank.services.model_registry_service import (
    ModelRegistryService,
    RegisterModelInput,
)

router = APIRouter(prefix="/models", tags=["models"])

DevUser = Annotated[AuthenticatedUser, Depends(require_role(Role.AI_DEVELOPER))]


def _service(session: DbSession, storage: StorageDep) -> ModelRegistryService:
    return ModelRegistryService(
        session=session,
        models=ModelArtifactRepository(session),
        storage=storage,
    )


@router.get("", response_model=Page[ModelOut])
async def list_models(
    session: DbSession,
    storage: StorageDep,
    _dev: DevUser,
    kind: ModelKind | None = Query(default=None),
    status_: Annotated[ModelStatus | None, Query(alias="status")] = None,
    seed_type_id: UUID | None = Query(default=None),
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[ModelOut]:
    svc = _service(session, storage)
    offset = (page - 1) * page_size
    rows, total = await svc.list(
        kind=kind,
        status=status_,
        seed_type_id=seed_type_id,
        limit=page_size,
        offset=offset,
    )
    items = [ModelOut.model_validate(r) for r in rows]
    return paginate(items, total=total, page=page, page_size=page_size)


@router.post(
    "",
    response_model=Envelope[ModelOut],
    status_code=status.HTTP_201_CREATED,
)
async def register_model(
    payload: ModelRegisterIn,
    request: Request,
    session: DbSession,
    storage: StorageDep,
    actor: DevUser,
) -> Envelope[ModelOut]:
    svc = _service(session, storage)
    row = await svc.register(
        actor_id=actor.id,
        payload=RegisterModelInput(
            name=payload.name,
            version=payload.version,
            kind=payload.kind,
            backend=payload.backend,
            artifact_uri=payload.artifact_uri,
            seed_type_id=payload.seed_type_id,
            config=payload.config,
            training_metadata=payload.training_metadata,
        ),
        ip=request.client.host if request.client else None,
    )
    return Envelope[ModelOut](data=ModelOut.model_validate(row))


@router.get("/{model_id}", response_model=Envelope[ModelOut])
async def get_model(
    model_id: UUID,
    session: DbSession,
    storage: StorageDep,
    _dev: DevUser,
) -> Envelope[ModelOut]:
    svc = _service(session, storage)
    row = await svc.get(model_id)
    return Envelope[ModelOut](data=ModelOut.model_validate(row))


@router.patch("/{model_id}", response_model=Envelope[ModelOut])
async def update_model_status(
    model_id: UUID,
    payload: ModelStatusUpdateIn,
    request: Request,
    session: DbSession,
    storage: StorageDep,
    actor: DevUser,
) -> Envelope[ModelOut]:
    svc = _service(session, storage)
    row = await svc.change_status(
        actor_id=actor.id,
        model_id=model_id,
        new_status=payload.status,
        ip=request.client.host if request.client else None,
    )
    return Envelope[ModelOut](data=ModelOut.model_validate(row))


@router.get("/{model_id}/performance", response_model=Envelope[ModelPerformanceOut])
async def model_performance(
    model_id: UUID,
    session: DbSession,
    storage: StorageDep,
    clickhouse: ClickHouseDep,
    metrics: ModelMetricRepoDep,
    _dev: DevUser,
) -> Envelope[ModelPerformanceOut]:
    """Aggregated performance for one model.

    Two sources merged into one envelope:

    * ``offline_metrics`` — Phase 7 ``model_metrics`` rows written by the
      experiment runner (always available).
    * ``rows`` — Phase 8 ClickHouse ``fact_inference`` aggregates
      (returns empty + a degradation ``note`` until that table exists).
    """
    # Make sure the model actually exists so we don't return empty silently
    # on a typo'd ID.
    await _service(session, storage).get(model_id)

    offline_rows = await metrics.list_for_model(model_id)
    offline = [OfflineMetricOut.model_validate(r) for r in offline_rows]

    note: str | None = None
    rows: list[dict[str, object]] = []
    try:
        rows = await clickhouse.query(
            "SELECT model_id, count() AS n, avg(latency_ms) AS avg_latency_ms "
            "FROM fact_inference WHERE model_id = {model_id:UUID} GROUP BY model_id",
            parameters={"model_id": str(model_id)},
        )
    except ExternalServiceError as exc:
        # ClickHouse / fact_inference may not exist yet (Phase 8). Degrade
        # gracefully rather than 500 on the AI dev's first call.
        note = f"clickhouse unavailable: {exc}"

    return Envelope[ModelPerformanceOut](
        data=ModelPerformanceOut(
            model_id=model_id,
            offline_metrics=offline,
            rows=rows,
            note=note,
        )
    )


__all__ = ["router"]
