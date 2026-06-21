"""Experiment + ExperimentResult + ModelMetric repositories.

Three small repos kept in one module — they share a domain (offline eval)
and never make sense without each other:

* :class:`ExperimentRepository` — CRUD on the run header. CAS for the
  worker's pending → running → succeeded/failed flips.
* :class:`ExperimentResultRepository` — bulk-insert per-item predictions
  from the worker.
* :class:`ModelMetricRepository` — denormalised summary metrics keyed by
  ``(model_id, dataset_id, metric_name)``. Phase 8 mirrors these to
  ClickHouse for serving ``GET /models/{id}/performance``; until then the
  endpoint reads them directly from PG.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import desc, func, select, update
from sqlalchemy.orm import selectinload

from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.models import (
    Experiment,
    ExperimentResult,
    ModelMetric,
)

from .base import Repository
from .scan_batch import CasResult

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal
    from uuid import UUID

    from seedbank.infrastructure.db.enums import ExperimentStatus


log = get_logger(__name__)


class ExperimentRepository(Repository[Experiment]):
    model = Experiment

    async def list_filtered(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        model_id: UUID | None = None,
        dataset_id: UUID | None = None,
        status: ExperimentStatus | None = None,
        created_by: UUID | None = None,
    ) -> list[Experiment]:
        stmt = select(Experiment)
        if model_id is not None:
            stmt = stmt.where(Experiment.model_id == model_id)
        if dataset_id is not None:
            stmt = stmt.where(Experiment.dataset_id == dataset_id)
        if status is not None:
            stmt = stmt.where(Experiment.status == status.value)
        if created_by is not None:
            stmt = stmt.where(Experiment.created_by == created_by)
        stmt = stmt.order_by(desc(Experiment.created_at)).limit(limit).offset(offset)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_filtered(
        self,
        *,
        model_id: UUID | None = None,
        dataset_id: UUID | None = None,
        status: ExperimentStatus | None = None,
        created_by: UUID | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(Experiment)
        if model_id is not None:
            stmt = stmt.where(Experiment.model_id == model_id)
        if dataset_id is not None:
            stmt = stmt.where(Experiment.dataset_id == dataset_id)
        if status is not None:
            stmt = stmt.where(Experiment.status == status.value)
        if created_by is not None:
            stmt = stmt.where(Experiment.created_by == created_by)
        return int((await self.session.execute(stmt)).scalar_one())

    async def get_with_results(self, experiment_id: UUID) -> Experiment | None:
        """Eager-load results so the detail view doesn't lazy-IO under
        async serialization."""
        stmt = (
            select(Experiment)
            .where(Experiment.id == experiment_id)
            .options(selectinload(Experiment.results))
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def cas_status(
        self,
        experiment_id: UUID,
        *,
        expected: ExperimentStatus,
        new: ExperimentStatus,
        set_started_at: bool = False,
        set_finished_at: bool = False,
        duration_ms: int | None = None,
        summary_metrics: dict[str, object] | None = None,
        mlflow_run_id: str | None = None,
    ) -> CasResult:
        """Atomic status flip. Returns a :class:`CasResult` whose ``won`` is
        true iff exactly one row was updated.

        Used by the worker to advance pending → running, then running →
        succeeded/failed. Concurrent worker retries lose the CAS and no-op
        rather than double-flipping the row. When ``set_started_at`` /
        ``set_finished_at`` is requested, the DB-side ``func.now()`` value
        is returned via ``RETURNING`` so the caller has the canonical
        timestamp without re-reading the row.
        """
        values: dict[str, object] = {"status": new.value}
        if set_started_at:
            values["started_at"] = func.now()
        if set_finished_at:
            values["finished_at"] = func.now()
        if duration_ms is not None:
            values["duration_ms"] = duration_ms
        if summary_metrics is not None:
            values["summary_metrics"] = summary_metrics
        if mlflow_run_id is not None:
            values["mlflow_run_id"] = mlflow_run_id

        stmt = (
            update(Experiment)
            .where(
                Experiment.id == experiment_id,
                Experiment.status == expected.value,
            )
            .values(**values)
            .returning(Experiment.started_at, Experiment.finished_at)
            # See ``ScanBatchRepository.cas_status``: ``synchronize_session=False``
            # plus ``RETURNING`` gives the caller the canonical post-update
            # values without ever touching the in-memory ORM object.
            .execution_options(synchronize_session=False)
        )
        row = (await self.session.execute(stmt)).first()
        log.info(
            "experiment.cas_status",
            experiment_id=str(experiment_id),
            **{"from": expected.value, "to": new.value},
            won=row is not None,
        )
        if row is None:
            return CasResult(won=False)
        return CasResult(won=True, started_at=row[0], finished_at=row[1])


class ExperimentResultRepository(Repository[ExperimentResult]):
    model = ExperimentResult

    async def add_many(self, rows: list[ExperimentResult]) -> None:
        if not rows:
            return
        self.session.add_all(rows)
        await self.session.flush()

    async def list_for_experiment(
        self, experiment_id: UUID, *, limit: int = 100, offset: int = 0
    ) -> list[ExperimentResult]:
        stmt = (
            select(ExperimentResult)
            .where(ExperimentResult.experiment_id == experiment_id)
            .order_by(ExperimentResult.id)
            .limit(limit)
            .offset(offset)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class ModelMetricRepository(Repository[ModelMetric]):
    model = ModelMetric

    async def upsert_for_experiment(
        self,
        *,
        model_id: UUID,
        dataset_id: UUID,
        metrics: dict[str, Decimal],
    ) -> None:
        """Replace summary metrics for a ``(model_id, dataset_id)`` pair.

        Each call clears prior rows for the same composite key and inserts
        the new values. Phase 8's ClickHouse mirror reads these directly,
        so consistency between the source rows and the latest experiment
        beats append-only history. An audit trail of past values lives in
        ``experiment_results`` and on the MLflow run.
        """
        from sqlalchemy import delete

        await self.session.execute(
            delete(ModelMetric).where(
                ModelMetric.model_id == model_id,
                ModelMetric.dataset_id == dataset_id,
            )
        )
        rows = [
            ModelMetric(
                model_id=model_id,
                dataset_id=dataset_id,
                metric_name=name,
                metric_value=value,
            )
            for name, value in metrics.items()
        ]
        if rows:
            self.session.add_all(rows)
        await self.session.flush()
        log.info(
            "model_metric.upsert",
            model_id=str(model_id),
            dataset_id=str(dataset_id),
            n=len(rows),
        )

    async def list_for_model(
        self, model_id: UUID, *, dataset_id: UUID | None = None
    ) -> list[ModelMetric]:
        stmt = (
            select(ModelMetric)
            .where(ModelMetric.model_id == model_id)
            .order_by(ModelMetric.dataset_id, ModelMetric.metric_name)
        )
        if dataset_id is not None:
            stmt = stmt.where(ModelMetric.dataset_id == dataset_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def latest_computed_at(
        self, model_id: UUID, dataset_id: UUID | None = None
    ) -> datetime | None:
        stmt = select(func.max(ModelMetric.computed_at)).where(ModelMetric.model_id == model_id)
        if dataset_id is not None:
            stmt = stmt.where(ModelMetric.dataset_id == dataset_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()
