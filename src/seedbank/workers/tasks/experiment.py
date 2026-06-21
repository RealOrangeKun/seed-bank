"""``seedbank.run_experiment`` — the offline-evaluation worker.

Celery counterpart to :class:`ExperimentService`: the API inserts an
``experiments`` row in ``status=pending`` and dispatches one task. This
task

1. opens a fresh ``AsyncSession`` (workers must NOT share the API engine),
2. flips the experiment from ``pending`` → ``running`` via CAS,
3. loads the model + dataset + every dataset item,
4. starts an MLflow run (best-effort; absence does not fail the run),
5. iterates each item: pulls bytes from MinIO ``seedbank-datasets``,
   runs the appropriate pipeline (detect or classify), records a
   per-item ``experiment_results`` row,
6. aggregates summary metrics, upserts ``model_metrics``, renders a
   Markdown report and uploads it to MinIO ``seedbank-experiments``,
7. logs to MLflow,
8. flips ``running`` → ``succeeded`` (or ``failed`` on any uncaught
   exception) with ``finished_at``, ``duration_ms``, ``summary_metrics``,
   ``mlflow_run_id`` set in the same UPDATE.

A failed item (bad ground-truth schema, decode error, backend exception)
is recorded on its row's ``error`` column and does NOT abort the run —
the experiment keeps going. The aggregate's ``items_failed`` counter
captures the count.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from seedbank.core.config import get_settings
from seedbank.core.exceptions import (
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)
from seedbank.core.ids import uuid7
from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.enums import ExperimentStatus, ModelKind
from seedbank.infrastructure.db.models import (
    DatasetItem,
    Experiment,
    ExperimentResult,
    ModelArtifact,
)
from seedbank.infrastructure.db.repositories import (
    DatasetItemRepository,
    DatasetRepository,
    ExperimentRepository,
    ExperimentResultRepository,
    ModelArtifactRepository,
    ModelMetricRepository,
)
from seedbank.infrastructure.ml.backends.base import (
    ClassificationConfig,
    DetectionConfig,
)
from seedbank.infrastructure.ml.pipeline.factory import (
    build_classify_pipeline,
    build_detect_pipeline,
)
from seedbank.infrastructure.mlflow import experiments as mlflow_runs
from seedbank.infrastructure.storage import get_storage
from seedbank.services.eval import (
    DetectionItemMetrics,
    GroundTruthBox,
    aggregate_classification,
    aggregate_detection,
    evaluate_classification_item,
    evaluate_detection_item,
    render_report,
)
from seedbank.services.eval.classification import ClassificationItemResult
from seedbank.workers.celery_app import celery_app
from seedbank.workers.runtime import run_async
from seedbank.workers.session import worker_session_scope

log = get_logger(__name__)


# ── Celery entry point ────────────────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="seedbank.run_experiment",
    bind=True,
    max_retries=1,
    default_retry_delay=10,
    autoretry_for=(ExternalServiceError,),
)
def run_experiment(
    self: object,  # noqa: ARG001 — Celery requires bind=True to accept self
    experiment_id: str,
) -> None:
    """Sync wrapper. Real work in the async coroutine."""
    run_async(_async_run_experiment(experiment_id=UUID(experiment_id)))


# ── Async orchestration ───────────────────────────────────────────────────────


@dataclass(slots=True)
class _Repos:
    experiments: ExperimentRepository
    results: ExperimentResultRepository
    models: ModelArtifactRepository
    datasets: DatasetRepository
    items: DatasetItemRepository
    metrics: ModelMetricRepository


async def _async_run_experiment(*, experiment_id: UUID) -> None:
    settings = get_settings()
    storage = get_storage()

    async with worker_session_scope() as session:
        repos = _Repos(
            experiments=ExperimentRepository(session),
            results=ExperimentResultRepository(session),
            models=ModelArtifactRepository(session),
            datasets=DatasetRepository(session),
            items=DatasetItemRepository(session),
            metrics=ModelMetricRepository(session),
        )

        # 1. Load the experiment row.
        experiment = await repos.experiments.get(experiment_id)
        if experiment is None:
            raise NotFoundError(f"experiment {experiment_id} not found")

        # 2. CAS pending → running. Loser is a no-op (concurrent retry).
        cas = await repos.experiments.cas_status(
            experiment.id,
            expected=ExperimentStatus.PENDING,
            new=ExperimentStatus.RUNNING,
            set_started_at=True,
        )
        await session.commit()
        log.info(
            "experiment.running",
            experiment_id=str(experiment.id),
            won_cas=cas.won,
        )
        if not cas.won:
            return

        # ``cas_status`` returned the canonical DB-side ``started_at`` via
        # ``RETURNING`` — use it for duration math instead of a Python clock.
        started_at = cas.started_at or datetime.now(UTC)

        # 3. Load model + dataset + items.
        model = await repos.models.get(experiment.model_id)
        if model is None:
            await _mark_failed(repos, experiment.id)
            await session.commit()
            raise NotFoundError(f"model_artifact {experiment.model_id} not found")

        dataset = await repos.datasets.get_active(experiment.dataset_id)
        if dataset is None:
            await _mark_failed(repos, experiment.id)
            await session.commit()
            raise NotFoundError(f"dataset {experiment.dataset_id} not found")

        # MVP cap — datasets larger than this should land later via paging.
        items = await repos.items.list_for_dataset(experiment.dataset_id, limit=10_000, offset=0)

        # 4. Start MLflow run (best-effort).
        run_id = mlflow_runs.start_run(
            experiment_id=experiment.id,
            experiment_name=experiment.name,
            model_id=model.id,
            dataset_id=dataset.id,
            kind=model.kind,
        )

        # 5. Run the appropriate eval flow.
        try:
            if model.kind == ModelKind.DETECTION.value:
                summary, metrics, items_evaluated, items_failed = await _run_detection_eval(
                    repos=repos,
                    storage=storage,
                    experiment=experiment,
                    model=model,
                    items=items,
                    bucket=settings.minio_bucket_datasets,
                )
            elif model.kind == ModelKind.CLASSIFICATION.value:
                summary, metrics, items_evaluated, items_failed = await _run_classification_eval(
                    repos=repos,
                    storage=storage,
                    experiment=experiment,
                    model=model,
                    items=items,
                    bucket=settings.minio_bucket_datasets,
                )
            else:
                raise ValidationError(f"Unsupported model kind {model.kind!r} for experiments.")
        except Exception:
            log.exception(
                "experiment.eval_failed",
                experiment_id=str(experiment.id),
            )
            await _mark_failed(repos, experiment.id, mlflow_run_id=run_id)
            await session.commit()
            if run_id:
                mlflow_runs.terminate(run_id, status="FAILED")
            raise

        # 6. Compute duration.
        finished_at = datetime.now(UTC)
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        # 7. Render markdown report and upload to MinIO.
        report_text = render_report(
            experiment_id=experiment.id,
            experiment_name=experiment.name,
            model_id=model.id,
            model_name=model.name,
            model_version=model.version,
            dataset_id=dataset.id,
            dataset_name=dataset.name,
            kind=model.kind,
            summary=summary,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            items_evaluated=items_evaluated,
            items_failed=items_failed,
            mlflow_run_id=run_id,
        )
        report_key = f"experiments/{experiment.id}/report.md"
        try:
            await storage.put_object(
                settings.minio_bucket_experiments,
                report_key,
                report_text.encode("utf-8"),
                "text/markdown",
            )
        except Exception as exc:
            log.warning(
                "experiment.report_upload_failed",
                experiment_id=str(experiment.id),
                error=repr(exc),
            )

        # 8. MLflow log_run (best-effort).
        if run_id:
            mlflow_runs.log_run(
                run_id=run_id,
                params={
                    "model_id": str(model.id),
                    "model_name": model.name,
                    "model_version": model.version,
                    "dataset_id": str(dataset.id),
                    "dataset_name": dataset.name,
                    "kind": model.kind,
                },
                metrics={
                    name: float(value)
                    for name, value in summary.items()
                    if isinstance(value, (int, float))
                },
                report_markdown=report_text,
            )

        # 9. Upsert ModelMetric rows.
        await repos.metrics.upsert_for_experiment(
            model_id=model.id,
            dataset_id=dataset.id,
            metrics=metrics,
        )

        # 10. CAS running → succeeded with full payload.
        await repos.experiments.cas_status(
            experiment.id,
            expected=ExperimentStatus.RUNNING,
            new=ExperimentStatus.SUCCEEDED,
            set_finished_at=True,
            duration_ms=duration_ms,
            summary_metrics=_jsonable_summary(summary),
            mlflow_run_id=run_id,
        )
        await session.commit()
        if run_id:
            mlflow_runs.terminate(run_id, status="FINISHED")

        log.info(
            "experiment.succeeded",
            experiment_id=str(experiment.id),
            model_id=str(model.id),
            dataset_id=str(dataset.id),
            items_evaluated=items_evaluated,
            items_failed=items_failed,
            duration_ms=duration_ms,
        )
        # DWH dual-write — fan out per-result fact rows + the model dim.
        from seedbank.workers.tasks.dwh import (  # local import keeps the module discoverable lazily
            SYNC_EXPERIMENT_RESULTS,
            dispatch_after_commit,
        )

        dispatch_after_commit(SYNC_EXPERIMENT_RESULTS, str(experiment.id))


# ── Eval flows ────────────────────────────────────────────────────────────────


async def _run_detection_eval(
    *,
    repos: _Repos,
    storage: Any,
    experiment: Experiment,
    model: ModelArtifact,
    items: list[DatasetItem],
    bucket: str,
) -> tuple[dict[str, Any], dict[str, Any], int, int]:
    """Run detection on every item, write per-item results, aggregate."""
    pipeline = build_detect_pipeline()
    cfg = _detection_config(model)

    item_metrics: list[DetectionItemMetrics] = []
    result_rows: list[ExperimentResult] = []
    failed = 0

    for item in items:
        try:
            image_bytes = await storage.get_object(bucket, item.image_storage_key)
            outcome = await pipeline.run(image=image_bytes, cfg=cfg, backend_name=model.backend)
            gt_boxes = _parse_detection_gt(item.ground_truth)
            metrics = evaluate_detection_item(
                predictions=outcome.detections,
                ground_truth=gt_boxes,
                latency_ms=outcome.latency_ms,
            )
            item_metrics.append(metrics)
            result_rows.append(
                ExperimentResult(
                    id=uuid7(),
                    experiment_id=experiment.id,
                    dataset_item_id=item.id,
                    predicted_boxes={
                        "boxes": [
                            {
                                "x": d.bbox.x,
                                "y": d.bbox.y,
                                "w": d.bbox.w,
                                "h": d.bbox.h,
                                "confidence": d.confidence,
                                "class_name": d.class_name,
                            }
                            for d in outcome.detections
                        ],
                        "tp": metrics.tp,
                        "fp": metrics.fp,
                        "fn": metrics.fn,
                    },
                    latency_ms=outcome.latency_ms,
                )
            )
        except Exception as exc:
            failed += 1
            log.exception(
                "experiment.item_failed",
                experiment_id=str(experiment.id),
                item_id=str(item.id),
                error=repr(exc),
            )
            result_rows.append(
                ExperimentResult(
                    id=uuid7(),
                    experiment_id=experiment.id,
                    dataset_item_id=item.id,
                    error=repr(exc),
                )
            )

    await repos.results.add_many(result_rows)

    aggregate = aggregate_detection(item_metrics, failed=failed)
    return (
        aggregate.as_summary(),
        aggregate.as_metrics(),
        aggregate.items_evaluated,
        aggregate.items_failed,
    )


async def _run_classification_eval(
    *,
    repos: _Repos,
    storage: Any,
    experiment: Experiment,
    model: ModelArtifact,
    items: list[DatasetItem],
    bucket: str,
) -> tuple[dict[str, Any], dict[str, Any], int, int]:
    """Run classification on every item, write per-item results, aggregate."""
    pipeline = build_classify_pipeline()
    cfg = _classification_config(model)

    item_results: list[ClassificationItemResult] = []
    result_rows: list[ExperimentResult] = []
    failed = 0

    for item in items:
        try:
            image_bytes = await storage.get_object(bucket, item.image_storage_key)
            outcome = await pipeline.run(crop=image_bytes, cfg=cfg, backend_name=model.backend)
            gt_label = _parse_classification_gt(item.ground_truth)
            item_results.append(
                evaluate_classification_item(
                    predicted=outcome.classification.label,
                    ground_truth=gt_label,
                    latency_ms=outcome.latency_ms,
                )
            )
            result_rows.append(
                ExperimentResult(
                    id=uuid7(),
                    experiment_id=experiment.id,
                    dataset_item_id=item.id,
                    predicted_boxes={
                        "label": outcome.classification.label,
                        "confidence": outcome.classification.confidence,
                        "ground_truth": gt_label,
                    },
                    latency_ms=outcome.latency_ms,
                )
            )
        except Exception as exc:
            failed += 1
            log.exception(
                "experiment.item_failed",
                experiment_id=str(experiment.id),
                item_id=str(item.id),
                error=repr(exc),
            )
            result_rows.append(
                ExperimentResult(
                    id=uuid7(),
                    experiment_id=experiment.id,
                    dataset_item_id=item.id,
                    error=repr(exc),
                )
            )

    await repos.results.add_many(result_rows)

    aggregate = aggregate_classification(item_results, failed=failed)
    return (
        aggregate.as_summary(),
        aggregate.as_metrics(),
        aggregate.items_evaluated,
        aggregate.items_failed,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _detection_config(model: ModelArtifact) -> DetectionConfig:
    cfg = model.config or {}
    return DetectionConfig(
        model_id=model.id,
        artifact_uri=model.artifact_uri,
        builder_key=str(cfg.get("builder_key", "default")),
        confidence_threshold=float(cfg.get("confidence_threshold", 0.5)),
        iou_threshold=float(cfg.get("iou_threshold", 0.5)),
        max_detections=int(cfg.get("max_detections", 300)),
        image_size=cfg.get("image_size"),
    )


def _classification_config(model: ModelArtifact) -> ClassificationConfig:
    cfg = model.config or {}
    return ClassificationConfig(
        model_id=model.id,
        artifact_uri=model.artifact_uri,
        builder_key=str(cfg.get("builder_key", "default")),
        threshold=float(cfg.get("threshold", 0.5)),
        image_size=int(cfg.get("image_size", 224)),
    )


def _parse_detection_gt(gt: dict[str, Any] | None) -> list[GroundTruthBox]:
    """Pull boxes out of a dataset item's ``ground_truth`` JSONB.

    Expected shape: ``{"kind": "detection", "boxes": [{"x":..,"y":..,
    "w":..,"h":..,"label":"good"}]}``. Missing boxes ⇒ empty list (an
    image with no annotated seeds is a valid eval case).
    """
    if not gt:
        return []
    boxes_raw = gt.get("boxes") or []
    if not isinstance(boxes_raw, list):
        raise ValidationError("ground_truth.boxes must be a list.")
    out: list[GroundTruthBox] = []
    for b in boxes_raw:
        if not isinstance(b, dict):
            raise ValidationError("ground_truth.boxes entries must be objects.")
        out.append(
            GroundTruthBox(
                x=float(b["x"]),
                y=float(b["y"]),
                w=float(b["w"]),
                h=float(b["h"]),
                label=str(b.get("label", "good")),
            )
        )
    return out


def _parse_classification_gt(gt: dict[str, Any] | None) -> str:
    """Pull the label out of a classification dataset item."""
    if not gt or "label" not in gt:
        raise ValidationError("ground_truth.label is required for classification.")
    return str(gt["label"])


def _jsonable_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Strip non-JSON-serialisable values (e.g. Decimal) before persisting
    to ``experiments.summary_metrics`` JSONB."""
    out: dict[str, Any] = {}
    for k, v in summary.items():
        if isinstance(v, (int, float, bool, str)):
            out[k] = v
        elif isinstance(v, dict):
            out[k] = {ik: iv for ik, iv in v.items() if isinstance(iv, (int, float, bool, str))}
        else:
            out[k] = float(v)
    return out


async def _mark_failed(
    repos: _Repos,
    experiment_id: UUID,
    *,
    mlflow_run_id: str | None = None,
) -> None:
    """Try ``running → failed``; if that loses, the row is already in a
    terminal state. Either way, no exception escapes the helper."""
    await repos.experiments.cas_status(
        experiment_id,
        expected=ExperimentStatus.RUNNING,
        new=ExperimentStatus.FAILED,
        set_finished_at=True,
        mlflow_run_id=mlflow_run_id,
    )


__all__ = ["run_experiment"]
