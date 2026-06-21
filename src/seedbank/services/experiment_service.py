"""Experiment service — the offline-eval use cases.

Phase 7 ships three operations through this service:

1. ``create_and_dispatch`` — validate the model + dataset references,
   insert the experiment row in ``status=pending``, commit, then push a
   Celery task on the ``experiments`` queue. Same ordering invariant as
   :class:`AnalysisService`: commit before dispatch so the worker never
   sees a missing row.
2. ``list_for_actor`` — paginated read with optional filter on model,
   dataset, status, or creator.
3. ``get_detail`` — single experiment with eager-loaded results + count.

Authorization is the router's responsibility (``require_role``); the
service raises domain errors only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from seedbank.core.exceptions import NotFoundError, ValidationError
from seedbank.core.ids import uuid7
from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.enums import ExperimentStatus, ModelStatus
from seedbank.infrastructure.db.models import AuditLog, Experiment
from seedbank.workers.celery_app import celery_app

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from seedbank.domain.user import AuthenticatedUser
    from seedbank.infrastructure.db.repositories import (
        DatasetRepository,
        ExperimentRepository,
        ExperimentResultRepository,
        ModelArtifactRepository,
    )


log = get_logger(__name__)

_RUN_TASK_NAME = "seedbank.run_experiment"
_RUN_TASK_QUEUE = "experiments"

# Models in ``archived`` cannot be evaluated — the artifact may have been
# deleted from MinIO. ``registered`` is allowed because that's the entire
# point: evaluate before promoting to staging/production.
_ELIGIBLE_MODEL_STATUSES = frozenset(
    {
        ModelStatus.REGISTERED.value,
        ModelStatus.STAGING.value,
        ModelStatus.PRODUCTION.value,
    }
)


class ExperimentService:
    """Use cases for ``/api/v1/experiments``."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        experiments: ExperimentRepository,
        results: ExperimentResultRepository,
        models: ModelArtifactRepository,
        datasets: DatasetRepository,
    ) -> None:
        self.session = session
        self.experiments = experiments
        self.results = results
        self.models = models
        self.datasets = datasets

    async def create_and_dispatch(
        self,
        *,
        actor: AuthenticatedUser,
        name: str,
        model_id: UUID,
        dataset_id: UUID,
        ip: str | None,
    ) -> Experiment:
        """Insert + dispatch one experiment.

        Validation order matches the surface area: model existence/status
        first (most likely to fail in dev), then dataset existence. The
        Experiment row is inserted in ``pending``; the worker advances it.
        """
        model = await self.models.get(model_id)
        if model is None:
            raise NotFoundError(f"model_artifact {model_id} not found")
        if model.status not in _ELIGIBLE_MODEL_STATUSES:
            raise ValidationError(
                f"Model {model.id} status={model.status} is not eligible for experiments."
            )

        dataset = await self.datasets.get_active(dataset_id)
        if dataset is None:
            raise NotFoundError(f"dataset {dataset_id} not found")

        experiment = Experiment(
            id=uuid7(),
            name=name,
            status=ExperimentStatus.PENDING.value,
            model_id=model.id,
            dataset_id=dataset.id,
            created_by=actor.id,
        )
        await self.experiments.add(experiment)

        self.session.add(
            AuditLog(
                actor_id=actor.id,
                action="experiment.dispatched",
                target_type="experiment",
                target_id=str(experiment.id),
                audit_metadata={
                    "model_id": str(model.id),
                    "dataset_id": str(dataset.id),
                },
                ip=ip,
            )
        )

        # Commit before dispatch — the worker must see the row.
        await self.session.commit()

        celery_app.send_task(
            _RUN_TASK_NAME,
            args=[str(experiment.id)],
            queue=_RUN_TASK_QUEUE,
        )

        log.info(
            "experiment.created",
            experiment_id=str(experiment.id),
            model_id=str(model.id),
            dataset_id=str(dataset.id),
            actor_id=str(actor.id),
        )
        return experiment

    async def list_for_actor(
        self,
        *,
        actor: AuthenticatedUser,
        page: int,
        page_size: int,
        model_id: UUID | None = None,
        dataset_id: UUID | None = None,
        status: ExperimentStatus | None = None,
    ) -> tuple[list[Experiment], int]:
        """Paginated listing.

        Visibility: experiments are AI-developer artefacts, not user data.
        The router has already gated to ``ai_developer``/``admin``; we
        return all rows matching the filters regardless of creator.
        """
        del actor  # role gate already enforced upstream
        offset = (page - 1) * page_size
        rows = await self.experiments.list_filtered(
            limit=page_size,
            offset=offset,
            model_id=model_id,
            dataset_id=dataset_id,
            status=status,
        )
        total = await self.experiments.count_filtered(
            model_id=model_id, dataset_id=dataset_id, status=status
        )
        return rows, total

    async def get_detail(self, experiment_id: UUID) -> tuple[Experiment, int]:
        """Detail view — returns ``(experiment, result_count)``.

        Eager-loads ``results`` so the listing endpoint can omit the JOIN.
        """
        experiment = await self.experiments.get_with_results(experiment_id)
        if experiment is None:
            raise NotFoundError("Experiment not found.")
        return experiment, len(experiment.results)


__all__ = ["ExperimentService"]
