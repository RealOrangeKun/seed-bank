"""Data-warehouse dual-write tasks (Phase 8).

For every meaningful OLTP event — a finished inference, a wave of new
detections, an experiment that just landed its results, a scan_batch
that changed status — an :mod:`api`/worker call site dispatches one of
these tasks **after the source row commits**. The task reads the
authoritative state back from Postgres, joins in the required
dimension rows, and writes both the dim and fact tuples into ClickHouse.

We deliberately do NOT pass the row contents in via Celery args. The
broker is at-least-once; the source of truth is Postgres. Reading
back means a duplicated task message is just a redundant idempotent
write — ``ReplacingMergeTree`` collapses it at merge time.

Failure posture: ClickHouse outages are :class:`ExternalServiceError`
and Celery retries with backoff. ``NotFoundError`` (the source row was
deleted out from under us) is non-retryable — the warehouse is allowed
to be eventually consistent on hard deletes.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.core.config import get_settings
from seedbank.core.exceptions import ExternalServiceError, NotFoundError
from seedbank.core.logging import get_logger
from seedbank.core.metrics import DWH_DISPATCH, DWH_TASK_DURATION
from seedbank.infrastructure.analytics import (
    AnalyticsRepository,
    DimModelRow,
    DimSeedTypeRow,
    DimUserRow,
    FactDetectionRow,
    FactExperimentResultRow,
    FactInferenceRow,
    FactScanBatchRow,
    get_clickhouse,
)
from seedbank.infrastructure.db.models import (
    Dataset,
    Experiment,
    ExperimentResult,
    Inference,
    ModelArtifact,
    ScanBatch,
    ScanImage,
    SeedDetection,
    SeedType,
    User,
)
from seedbank.workers.celery_app import celery_app
from seedbank.workers.runtime import run_async
from seedbank.workers.session import worker_session_scope

log = get_logger(__name__)


# ── Task names + queue ─────────────────────────────────────────────────────

DWH_QUEUE = "dwh"

SYNC_INFERENCE = "seedbank.dwh.sync_inference"
SYNC_DETECTIONS = "seedbank.dwh.sync_detections"
SYNC_EXPERIMENT_RESULTS = "seedbank.dwh.sync_experiment_results"
SYNC_SCAN_BATCH = "seedbank.dwh.sync_scan_batch"


# ── Celery wrappers (sync) ─────────────────────────────────────────────────


def _run_timed(
    task_name: str, fn: Callable[[UUID], Coroutine[Any, Any, None]], arg_id: str
) -> None:
    """Run an async sync-task body and observe its duration + outcome.

    The label ``result`` lets dashboards split healthy throughput
    (``ok``) from retry-driving failures (``error``) and from genuine
    "the source row was deleted" non-retryables (``not_found``).
    Re-raises so Celery's retry/ack semantics are unchanged.
    """
    start = perf_counter()
    result = "ok"
    try:
        run_async(fn(UUID(arg_id)))
    except NotFoundError:
        result = "not_found"
        raise
    except Exception:
        result = "error"
        raise
    finally:
        DWH_TASK_DURATION.labels(task=task_name, result=result).observe(perf_counter() - start)


@celery_app.task(  # type: ignore[untyped-decorator]
    name=SYNC_INFERENCE,
    bind=True,
    max_retries=5,
    default_retry_delay=15,
    autoretry_for=(ExternalServiceError,),
    retry_backoff=True,
)
def sync_inference(self: object, inference_id: str) -> None:  # noqa: ARG001
    _run_timed(SYNC_INFERENCE, _async_sync_inference, inference_id)


@celery_app.task(  # type: ignore[untyped-decorator]
    name=SYNC_DETECTIONS,
    bind=True,
    max_retries=5,
    default_retry_delay=15,
    autoretry_for=(ExternalServiceError,),
    retry_backoff=True,
)
def sync_detections(self: object, inference_id: str) -> None:  # noqa: ARG001
    _run_timed(SYNC_DETECTIONS, _async_sync_detections, inference_id)


@celery_app.task(  # type: ignore[untyped-decorator]
    name=SYNC_EXPERIMENT_RESULTS,
    bind=True,
    max_retries=5,
    default_retry_delay=15,
    autoretry_for=(ExternalServiceError,),
    retry_backoff=True,
)
def sync_experiment_results(self: object, experiment_id: str) -> None:  # noqa: ARG001
    _run_timed(SYNC_EXPERIMENT_RESULTS, _async_sync_experiment_results, experiment_id)


@celery_app.task(  # type: ignore[untyped-decorator]
    name=SYNC_SCAN_BATCH,
    bind=True,
    max_retries=5,
    default_retry_delay=15,
    autoretry_for=(ExternalServiceError,),
    retry_backoff=True,
)
def sync_scan_batch(self: object, batch_id: str) -> None:  # noqa: ARG001
    _run_timed(SYNC_SCAN_BATCH, _async_sync_scan_batch, batch_id)


# ── Async cores ────────────────────────────────────────────────────────────
#
# Every task uses the worker-process-cached :func:`get_clickhouse` helper
# so the urllib3 pool inside ``clickhouse-connect`` is reused across task
# runs. The async wrapper is a thread-pool over the sync client — it has
# no event-loop-bound state, so re-use across ``asyncio.run`` calls is
# safe (unlike asyncpg, which is why Postgres still uses
# ``worker_session_scope`` per task).


async def _async_sync_inference(inference_id: UUID) -> None:
    async with worker_session_scope() as session:
        inference, image, batch, model = await _load_inference_chain(session, inference_id)
        seed_type = (
            await _load_seed_type(session, model.seed_type_id) if model.seed_type_id else None
        )
        user = await _require_user(session, batch.user_id)

    client = await get_clickhouse()
    repo = AnalyticsRepository(client)
    await repo.upsert_user(_dim_user(user))
    await repo.upsert_model(_dim_model(model))
    if seed_type is not None:
        await repo.upsert_seed_type(_dim_seed_type(seed_type))
    await repo.insert_inference(
        FactInferenceRow(
            inference_id=inference.id,
            image_id=image.id,
            batch_id=batch.id,
            user_id=batch.user_id,
            model_id=model.id,
            seed_type_id=model.seed_type_id,
            backend=model.backend,
            model_kind=model.kind,
            latency_ms=inference.latency_ms,
            has_error=bool(inference.error),
            occurred_at=inference.occurred_at,
        )
    )
    log.info("dwh.inference_synced", inference_id=str(inference_id))


async def _async_sync_detections(inference_id: UUID) -> None:
    async with worker_session_scope() as session:
        inference, image, batch, model = await _load_inference_chain(session, inference_id)
        stmt = select(SeedDetection).where(SeedDetection.inference_id == inference_id)
        detections = list((await session.execute(stmt)).scalars().all())
        seed_type_ids = {d.seed_type_id for d in detections if d.seed_type_id is not None}
        seed_types: dict[UUID, SeedType] = {}
        if seed_type_ids:
            st_stmt = select(SeedType).where(SeedType.id.in_(seed_type_ids))
            for st in (await session.execute(st_stmt)).scalars().all():
                seed_types[st.id] = st

    if not detections:
        log.info("dwh.detections_skipped", inference_id=str(inference_id), reason="empty")
        return

    client = await get_clickhouse()
    repo = AnalyticsRepository(client)
    for st in seed_types.values():
        await repo.upsert_seed_type(_dim_seed_type(st))
    await repo.insert_detections(
        FactDetectionRow(
            detection_id=d.id,
            inference_id=inference.id,
            image_id=image.id,
            batch_id=batch.id,
            user_id=batch.user_id,
            model_id=model.id,
            seed_type_id=d.seed_type_id,
            quality=d.quality,
            confidence=d.confidence,
            detection_confidence=d.detection_confidence or d.confidence,
            box_x_norm=d.box_x_norm,
            box_y_norm=d.box_y_norm,
            box_w_norm=d.box_w_norm,
            box_h_norm=d.box_h_norm,
            width_px=d.width_px,
            height_px=d.height_px,
            area_px=d.area_px,
            aspect_ratio=d.aspect_ratio,
            occurred_at=inference.occurred_at,
        )
        for d in detections
    )
    log.info(
        "dwh.detections_synced",
        inference_id=str(inference_id),
        n=len(detections),
    )


async def _async_sync_experiment_results(experiment_id: UUID) -> None:
    async with worker_session_scope() as session:
        experiment = await session.get(Experiment, experiment_id)
        if experiment is None:
            raise NotFoundError(f"experiment {experiment_id} not found")
        model = await session.get(ModelArtifact, experiment.model_id)
        dataset = await session.get(Dataset, experiment.dataset_id)
        if model is None or dataset is None:
            raise NotFoundError(f"experiment {experiment_id}: parent model or dataset missing")
        user = (
            await session.get(User, experiment.created_by)
            if experiment.created_by is not None
            else None
        )
        stmt = select(ExperimentResult).where(ExperimentResult.experiment_id == experiment_id)
        results = list((await session.execute(stmt)).scalars().all())

    if not results:
        log.info(
            "dwh.experiment_results_skipped",
            experiment_id=str(experiment_id),
            reason="empty",
        )
        return

    occurred_at = experiment.finished_at or experiment.started_at or datetime.now(UTC)
    user_id = user.id if user is not None else None

    client = await get_clickhouse()
    repo = AnalyticsRepository(client)
    if user is not None:
        await repo.upsert_user(_dim_user(user))
    await repo.upsert_model(_dim_model(model))
    await repo.insert_experiment_results(
        FactExperimentResultRow(
            result_id=r.id,
            experiment_id=experiment.id,
            dataset_id=dataset.id,
            dataset_item_id=r.dataset_item_id,
            model_id=model.id,
            user_id=user_id,
            has_error=bool(r.error),
            latency_ms=r.latency_ms,
            occurred_at=occurred_at,
        )
        for r in results
    )
    log.info(
        "dwh.experiment_results_synced",
        experiment_id=str(experiment_id),
        n=len(results),
    )


async def _async_sync_scan_batch(batch_id: UUID) -> None:
    async with worker_session_scope() as session:
        batch = await session.get(ScanBatch, batch_id)
        if batch is None:
            raise NotFoundError(f"scan_batch {batch_id} not found")
        user = await _require_user(session, batch.user_id)
        image_count = (
            await session.scalar(
                select(func.count(ScanImage.id)).where(ScanImage.batch_id == batch_id)
            )
            or 0
        )

    client = await get_clickhouse()
    repo = AnalyticsRepository(client)
    await repo.upsert_user(_dim_user(user))
    await repo.upsert_scan_batch(
        FactScanBatchRow(
            batch_id=batch.id,
            user_id=batch.user_id,
            supplier_id=batch.supplier_id,
            status=batch.status,
            source=batch.source,
            image_count=int(image_count),
            duration_ms=batch.duration_ms,
            submitted_at=batch.submitted_at,
            started_at=batch.started_at,
            finished_at=batch.finished_at,
            geo_country_code=(batch.geo_country_code or ""),
        )
    )
    log.info(
        "dwh.scan_batch_synced",
        batch_id=str(batch_id),
        status=batch.status,
        image_count=int(image_count),
    )


# ── Loaders ────────────────────────────────────────────────────────────────


async def _load_inference_chain(
    session: AsyncSession, inference_id: UUID
) -> tuple[Inference, ScanImage, ScanBatch, ModelArtifact]:
    inference = await session.get(Inference, inference_id)
    if inference is None:
        raise NotFoundError(f"inference {inference_id} not found")
    image = await session.get(ScanImage, inference.image_id)
    if image is None:
        raise NotFoundError(f"scan_image {inference.image_id} not found")
    batch = await session.get(ScanBatch, image.batch_id)
    if batch is None:
        raise NotFoundError(f"scan_batch {image.batch_id} not found")
    model = await session.get(ModelArtifact, inference.model_id)
    if model is None:
        raise NotFoundError(f"model_artifact {inference.model_id} not found")
    return inference, image, batch, model


async def _load_seed_type(session: AsyncSession, seed_type_id: UUID) -> SeedType | None:
    return await session.get(SeedType, seed_type_id)


async def _require_user(session: AsyncSession, user_id: UUID) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise NotFoundError(f"user {user_id} not found")
    return user


# ── Builders ───────────────────────────────────────────────────────────────


def _dim_user(user: User) -> DimUserRow:
    return DimUserRow(
        user_id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        is_verified=user.is_verified,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _dim_seed_type(seed_type: SeedType) -> DimSeedTypeRow:
    return DimSeedTypeRow(
        seed_type_id=seed_type.id,
        code=seed_type.code,
        display_name=seed_type.display_name,
        default_confidence_threshold=seed_type.default_confidence_threshold,
        created_at=seed_type.created_at,
        updated_at=seed_type.updated_at,
    )


def _dim_model(model: ModelArtifact) -> DimModelRow:
    return DimModelRow(
        model_id=model.id,
        name=model.name,
        version=model.version,
        kind=model.kind,
        backend=model.backend,
        seed_type_id=model.seed_type_id,
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


# ── Dispatch helper for callers ────────────────────────────────────────────


def dispatch_after_commit(task_name: str, *args: Any) -> None:
    """Best-effort fire-and-forget enqueue.

    Wraps :py:meth:`celery_app.send_task` so a broker outage during a
    request never poisons the API response. The OLTP commit already
    happened; losing the warehouse delta is recoverable through a
    backfill job.

    Honors the ``dwh_enabled`` setting — when false, dispatches are
    no-ops. This keeps the eager test path from inline-invoking the
    sync tasks against an absent ClickHouse container.

    Increments :data:`seedbank.core.metrics.DWH_DISPATCH` so operators can
    alert on dispatch failure rate (Finding #5). The label ``result`` is
    one of ``ok`` / ``disabled`` / ``error``.
    """
    if not get_settings().dwh_enabled:
        DWH_DISPATCH.labels(task=task_name, result="disabled").inc()
        return
    try:
        celery_app.send_task(task_name, args=list(args), queue=DWH_QUEUE)
    except Exception as exc:
        DWH_DISPATCH.labels(task=task_name, result="error").inc()
        # ``repr(exc)`` on a redis-py / kombu exception can carry the broker
        # URL with credentials. Log the exception class + the scrubbed
        # message instead.
        log.warning(
            "dwh.dispatch_failed",
            task=task_name,
            error_type=type(exc).__name__,
            error_msg=_scrub_broker_url(str(exc)),
        )
    else:
        DWH_DISPATCH.labels(task=task_name, result="ok").inc()


_BROKER_URL_RE = re.compile(r"(redis|amqp|sentinel|rediss)://[^@\s]+@")


def _scrub_broker_url(message: str) -> str:
    """Replace ``scheme://user:pass@host`` with ``scheme://***@`` so a leaking
    driver exception cannot put the broker password into our logs."""
    return _BROKER_URL_RE.sub(r"\1://***@", message)


__all__ = [
    "DWH_QUEUE",
    "SYNC_DETECTIONS",
    "SYNC_EXPERIMENT_RESULTS",
    "SYNC_INFERENCE",
    "SYNC_SCAN_BATCH",
    "dispatch_after_commit",
    "sync_detections",
    "sync_experiment_results",
    "sync_inference",
    "sync_scan_batch",
]
