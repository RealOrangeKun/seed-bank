"""``/api/v1/experiments`` — offline-eval orchestration endpoints.

POST creates an experiment row and dispatches the runner; the worker (in
:mod:`seedbank.workers.tasks.experiment`) does the heavy lifting and
flips the status. GET /experiments returns a paginated list filtered by
``model_id`` / ``dataset_id`` / ``status``. GET /experiments/{id} returns
the summary; the per-item results have their own paginated endpoint.

Role gate: ``ai_developer`` (admins implicitly satisfy).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from seedbank.api.deps import (
    CurrentUser,
    ExperimentServiceDep,
    require_role,
)
from seedbank.domain.user import Role
from seedbank.infrastructure.db.enums import ExperimentStatus
from seedbank.schemas.common import Envelope, Page, paginate
from seedbank.schemas.experiment import (
    ExperimentCreateIn,
    ExperimentDetailOut,
    ExperimentSummaryOut,
)

router = APIRouter(prefix="/experiments", tags=["experiments"])

_AI_GATE = Depends(require_role(Role.AI_DEVELOPER))


@router.post(
    "",
    response_model=Envelope[ExperimentSummaryOut],
    status_code=201,
    dependencies=[_AI_GATE],
)
async def create_experiment(
    body: ExperimentCreateIn,
    actor: CurrentUser,
    service: ExperimentServiceDep,
    request: Request,
) -> Envelope[ExperimentSummaryOut]:
    experiment = await service.create_and_dispatch(
        actor=actor,
        name=body.name,
        model_id=body.model_id,
        dataset_id=body.dataset_id,
        ip=request.client.host if request.client else None,
    )
    return Envelope[ExperimentSummaryOut](data=ExperimentSummaryOut.model_validate(experiment))


@router.get(
    "",
    response_model=Page[ExperimentSummaryOut],
    dependencies=[_AI_GATE],
)
async def list_experiments(
    actor: CurrentUser,
    service: ExperimentServiceDep,
    model_id: Annotated[UUID | None, Query()] = None,
    dataset_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[ExperimentStatus | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> Page[ExperimentSummaryOut]:
    rows, total = await service.list_for_actor(
        actor=actor,
        page=page,
        page_size=page_size,
        model_id=model_id,
        dataset_id=dataset_id,
        status=status,
    )
    items = [ExperimentSummaryOut.model_validate(r) for r in rows]
    return paginate(items, total=total, page=page, page_size=page_size)


@router.get(
    "/{experiment_id}",
    response_model=Envelope[ExperimentDetailOut],
    dependencies=[_AI_GATE],
)
async def get_experiment(
    experiment_id: UUID,
    service: ExperimentServiceDep,
) -> Envelope[ExperimentDetailOut]:
    experiment, count = await service.get_detail(experiment_id)
    out = ExperimentDetailOut.model_validate(experiment).model_copy(update={"result_count": count})
    return Envelope[ExperimentDetailOut](data=out)


__all__ = ["router"]
