"""``seedbank.analyze_image`` — the inference worker task.

This is the Celery counterpart to :class:`AnalysisService`: the API uploads
the image to MinIO, commits ``scan_batches``/``scan_images``, then dispatches
one task per image. This task

1. opens a fresh ``AsyncSession`` (workers must NOT share the API engine),
2. flips the batch from ``pending`` → ``running`` on first arrival,
3. resolves a detection model (override or via :class:`TrafficRouter`),
4. runs detection, persists ``inferences`` + ``seed_detections`` rows,
5. resolves a classification model and labels every detected crop,
6. flips the batch to ``succeeded`` / ``partial`` / ``failed`` once every
   image has either a detect inference or a recorded error.

Errors are categorised:

* ``ExternalServiceError`` (MinIO / Redis hiccups) — surfaced through
  ``autoretry_for`` so Celery retries up to ``max_retries`` times.
* ``NotFoundError`` / ``ValidationError`` / ``ForbiddenError`` —
  non-recoverable; the task fails immediately.
* Any other exception during detect — written onto the inference row's
  ``error`` field and the batch is marked ``failed``.
* Any exception during classify (after detect persisted) — detect data
  stays, the classify inference's ``error`` is recorded, and the batch
  flips to ``partial``.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO
from typing import TYPE_CHECKING
from uuid import UUID

from PIL import Image
from sqlalchemy import func, select, update

from seedbank.core.config import get_settings
from seedbank.core.exceptions import (
    ExternalServiceError,
    ForbiddenError,
    ModelNotReadyError,
    NotFoundError,
    ValidationError,
)
from seedbank.core.ids import uuid7
from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.enums import (
    BatchStatus,
    ModelKind,
    ModelStatus,
    SeedQuality,
)
from seedbank.infrastructure.db.models import (
    Inference,
    ModelArtifact,
    ScanBatch,
    ScanImage,
    SeedDetection,
)
from seedbank.infrastructure.db.repositories import (
    InferenceRepository,
    ModelArtifactRepository,
    ScanBatchRepository,
    ScanImageRepository,
    SeedDetectionRepository,
    SeedTypeRepository,
)
from seedbank.infrastructure.ml.backends.base import (
    ClassificationConfig,
    DetectionConfig,
)
from seedbank.infrastructure.ml.pipeline.factory import (
    build_classify_pipeline,
    build_detect_pipeline,
)
from seedbank.infrastructure.storage import get_storage
from seedbank.services.traffic_router import TrafficRouter
from seedbank.workers.celery_app import celery_app
from seedbank.workers.runtime import get_worker_redis, run_async
from seedbank.workers.session import worker_session_scope
from seedbank.workers.tasks.dwh import (
    SYNC_DETECTIONS,
    SYNC_INFERENCE,
    SYNC_SCAN_BATCH,
    dispatch_after_commit,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from seedbank.infrastructure.ml.backends.base import Detection
    from seedbank.infrastructure.ml.pipeline.classify import ClassifyPipeline
    from seedbank.infrastructure.ml.pipeline.detect import DetectPipeline

log = get_logger(__name__)


# Allowed override statuses — registered/archived overrides are rejected so
# an experiment-only model isn't accidentally used to serve a user request.
_OVERRIDE_ALLOWED_STATUSES = frozenset({ModelStatus.STAGING.value, ModelStatus.PRODUCTION.value})


# ── Celery entry point ────────────────────────────────────────────────────────


@celery_app.task(  # type: ignore[untyped-decorator]
    name="seedbank.analyze_image",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    autoretry_for=(ExternalServiceError,),
)
def analyze_image(
    self: object,  # noqa: ARG001 — Celery requires `bind=True` to accept self
    image_id: str,
    model_id_override: str | None = None,
    seed_type_id: str | None = None,
) -> None:
    """Sync Celery wrapper. The real work lives in the async coroutine."""
    run_async(
        _async_analyze_image(
            image_id=UUID(image_id),
            model_id_override=(UUID(model_id_override) if model_id_override else None),
            seed_type_id=UUID(seed_type_id) if seed_type_id else None,
        )
    )


# ── Async orchestration ───────────────────────────────────────────────────────


@dataclass(slots=True)
class _Repos:
    """Bundle of the repositories every helper needs. Keeps signatures sane."""

    batches: ScanBatchRepository
    images: ScanImageRepository
    models: ModelArtifactRepository
    inferences: InferenceRepository
    detections: SeedDetectionRepository
    seed_types: SeedTypeRepository


async def _async_analyze_image(
    *,
    image_id: UUID,
    model_id_override: UUID | None,
    seed_type_id: UUID | None,
) -> None:
    settings = get_settings()
    storage = get_storage()
    # The redis client and DB engine are process-scoped (built in the
    # worker_process_init signal) and bound to the persistent loop —
    # safe to reuse across tasks; nothing to close here.
    redis = get_worker_redis()
    async with worker_session_scope() as session:
        repos = _Repos(
            batches=ScanBatchRepository(session),
            images=ScanImageRepository(session),
            models=ModelArtifactRepository(session),
            inferences=InferenceRepository(session),
            detections=SeedDetectionRepository(session),
            seed_types=SeedTypeRepository(session),
        )

        # 1. Load image + batch. Missing rows are non-recoverable.
        image = await repos.images.get(image_id)
        if image is None:
            raise NotFoundError(f"scan_image {image_id} not found")
        batch = await repos.batches.get(image.batch_id)
        if batch is None:
            raise NotFoundError(f"scan_batch {image.batch_id} not found")

        # 2. CAS pending → running. Loser of the race is a no-op.
        # ``cas_status`` returns the canonical DB-side ``started_at`` via
        # ``RETURNING`` so we never read the stale in-memory ORM column.
        # On a lost CAS, fall back to the row's existing ``started_at``
        # (set by whichever worker won) — read it from the DB, not from
        # the in-memory object, since that one is also stale.
        cas = await repos.batches.cas_status(
            batch.id,
            expected=BatchStatus.PENDING,
            new=BatchStatus.RUNNING,
            set_started_at=True,
        )
        await session.commit()
        log.info(
            "analyze.batch_running",
            batch_id=str(batch.id),
            image_id=str(image.id),
            won_cas=cas.won,
        )
        if cas.won:
            # First task to win the CAS owns the running-state DWH refresh.
            dispatch_after_commit(SYNC_SCAN_BATCH, str(batch.id))
            batch_started_at = cas.started_at
        else:
            # Loser of the CAS: another worker already flipped the row to
            # RUNNING and stamped ``started_at``. Re-fetch through the
            # async path so we have an up-to-date timestamp for duration
            # bookkeeping.
            refreshed = await repos.batches.get(batch.id)
            batch_started_at = refreshed.started_at if refreshed else None

        # 3. Pull image bytes from MinIO. Failure here -> ExternalServiceError
        # which Celery retries via ``autoretry_for``.
        image_bytes = await storage.get_object(settings.minio_bucket_images, image.storage_key)

        # 4. Build pipelines + traffic router.
        detect_pipeline = build_detect_pipeline()
        classify_pipeline = build_classify_pipeline()
        router = TrafficRouter(session=session, models=repos.models, redis=redis)

        # 5. Resolve + run detect. Errors are recorded and re-raised.
        try:
            detect_model = await _resolve_detect_model(
                repos=repos,
                router=router,
                model_id_override=model_id_override,
                seed_type_id=seed_type_id,
                user_id=batch.user_id,
            )
        except ModelNotReadyError:
            # No detector is routable for this segment — a config/ops state, not
            # a code bug. Tell the user plainly so the app doesn't show a blank
            # failure (the mobile flow sends no seed type and hits this first).
            await _mark_batch_failed(
                repos=repos,
                batch_id=batch.id,
                started_at=batch_started_at,
                error_message=(
                    "No detection model is available to analyze this scan. "
                    "An administrator must register and promote a detection model."
                ),
            )
            await session.commit()
            dispatch_after_commit(SYNC_SCAN_BATCH, str(batch.id))
            raise
        except Exception:
            await _mark_batch_failed(
                repos=repos,
                batch_id=batch.id,
                started_at=batch_started_at,
                error_message=(
                    "Could not start analysis: the requested model is invalid or unavailable."
                ),
            )
            await session.commit()
            dispatch_after_commit(SYNC_SCAN_BATCH, str(batch.id))
            raise

        detect_inference = await _run_detect_and_persist(
            session=session,
            repos=repos,
            pipeline=detect_pipeline,
            image=image,
            image_bytes=image_bytes,
            detect_model=detect_model,
            seed_type_id=seed_type_id,
            batch_id=batch.id,
            started_at=batch_started_at,
        )

        # 6. Resolve + run classify, per seed type. Each detection carries its
        # own ``seed_type_id`` (request override, or the detector's class), so
        # coffee crops go to the coffee classifier and maize to the maize one.
        # Failures here are non-fatal: detect data is already persisted; we
        # degrade the batch to ``partial`` instead of ``failed``.
        classify_failed = False
        try:
            classify_failed = await _classify_all_detections(
                session=session,
                repos=repos,
                router=router,
                pipeline=classify_pipeline,
                image=image,
                image_bytes=image_bytes,
                detect_inference=detect_inference,
                user_id=batch.user_id,
                batch_id=batch.id,
            )
        except Exception as exc:
            log.exception(
                "analyze.classify_failed",
                batch_id=str(batch.id),
                image_id=str(image.id),
                error=repr(exc),
            )
            classify_failed = True

        # 7. Finalise the batch if every image is now accounted for.
        await _finalize_batch_if_done(
            session=session,
            repos=repos,
            batch_id=batch.id,
            started_at=batch_started_at,
            had_classify_failure=classify_failed,
        )


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _resolve_detect_model(
    *,
    repos: _Repos,
    router: TrafficRouter,
    model_id_override: UUID | None,
    seed_type_id: UUID | None,
    user_id: UUID,
) -> ModelArtifact:
    """Pick the detection model — override path or traffic router."""
    if model_id_override is not None:
        model = await repos.models.get(model_id_override)
        if model is None:
            raise NotFoundError(f"model_artifact {model_id_override} not found")
        if model.kind != ModelKind.DETECTION.value:
            raise ValidationError(f"Model {model.id} is kind={model.kind}, not detection.")
        if model.status not in _OVERRIDE_ALLOWED_STATUSES:
            raise ForbiddenError(
                f"Model {model.id} status={model.status} is not eligible for analyze override."
            )
        return model

    model_id = await router.select_model(
        kind=ModelKind.DETECTION,
        seed_type_id=seed_type_id,
        user_id=user_id,
    )
    model = await repos.models.get(model_id)
    if model is None:  # pragma: no cover — router promised it exists
        raise NotFoundError(f"model_artifact {model_id} not found")
    return model


async def _resolve_classify_model(
    *,
    router: TrafficRouter,
    models: ModelArtifactRepository,
    seed_type_id: UUID | None,
    user_id: UUID,
    batch_id: UUID,
) -> ModelArtifact | None:
    """Pick the classification model. Returns ``None`` (with a log) when no
    classifier is registered for the segment — classification is optional."""
    try:
        model_id = await router.select_model(
            kind=ModelKind.CLASSIFICATION,
            seed_type_id=seed_type_id,
            user_id=user_id,
        )
    except ModelNotReadyError:
        log.info(
            "analyze.classify_skipped",
            reason="no_model",
            batch_id=str(batch_id),
            seed_type_id=str(seed_type_id) if seed_type_id else None,
        )
        return None
    return await models.get(model_id)


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


async def _run_detect_and_persist(
    *,
    session: AsyncSession,
    repos: _Repos,
    pipeline: DetectPipeline,
    image: ScanImage,
    image_bytes: bytes,
    detect_model: ModelArtifact,
    seed_type_id: UUID | None,
    batch_id: UUID,
    started_at: datetime | None,
) -> Inference:
    """Run detect, write the inference + detection rows, commit."""
    inference = await repos.inferences.add_inference(
        image_id=image.id,
        model_id=detect_model.id,
        backend=detect_model.backend,
        latency_ms=None,
    )

    try:
        outcome = await pipeline.run(
            image=image_bytes,
            cfg=_detection_config(detect_model),
            backend_name=detect_model.backend,
        )
    except Exception as exc:
        # Best-effort: record on the row we just created, commit, mark batch.
        log.exception(
            "analyze.detect_failed",
            batch_id=str(batch_id),
            image_id=str(image.id),
            model_id=str(detect_model.id),
            error=repr(exc),
        )
        with suppress(Exception):
            await repos.inferences.set_error(inference.id, repr(exc))
            await session.commit()
        await _mark_batch_failed(
            repos=repos,
            batch_id=batch_id,
            started_at=started_at,
            error_message="Detection failed while processing the image.",
        )
        await session.commit()
        dispatch_after_commit(SYNC_SCAN_BATCH, str(batch_id))
        raise

    # Update latency now that we have it.
    await session.execute(
        update(Inference)
        .where(Inference.id == inference.id)
        .values(latency_ms=outcome.latency_ms)
        .execution_options(synchronize_session=False)
    )

    # Resolve each detection's seed type. An explicit batch-level
    # ``seed_type_id`` (from the request) always wins; otherwise we map the
    # detector's class name ("coffee"/"maize") to its catalog id so per-type
    # quality classifiers can be routed downstream.
    code_to_id = {} if seed_type_id is not None else await repos.seed_types.code_to_id()
    rows = [
        _build_seed_detection(
            inference_id=inference.id,
            seed_type_id=(
                seed_type_id
                if seed_type_id is not None
                else code_to_id.get((det.class_name or "").lower())
            ),
            detection=det,
            image=image,
        )
        for det in outcome.detections
    ]
    await repos.detections.add_many(rows)
    await session.commit()

    log.info(
        "analyze.detect_persisted",
        batch_id=str(batch_id),
        image_id=str(image.id),
        inference_id=str(inference.id),
        n_detections=len(rows),
        latency_ms=outcome.latency_ms,
    )
    dispatch_after_commit(SYNC_INFERENCE, str(inference.id))
    dispatch_after_commit(SYNC_DETECTIONS, str(inference.id))
    return inference


def _build_seed_detection(
    *,
    inference_id: UUID,
    seed_type_id: UUID | None,
    detection: Detection,
    image: ScanImage,
) -> SeedDetection:
    """Convert a backend ``Detection`` DTO into a persisted row.

    Confidence is ``NUMERIC(5,4)`` and bbox columns are ``NUMERIC(7,6)`` —
    we round and pass ``Decimal`` so SQLAlchemy doesn't coerce float into
    a mismatched scale.
    """
    box = detection.bbox
    width_px = int(box.w * image.width) if image.width else None
    height_px = int(box.h * image.height) if image.height else None
    area_px = width_px * height_px if width_px is not None and height_px is not None else None
    aspect_ratio: Decimal | None = None
    if width_px and height_px:
        aspect_ratio = Decimal(str(round(width_px / height_px, 4)))

    return SeedDetection(
        id=uuid7(),
        inference_id=inference_id,
        seed_type_id=seed_type_id,
        confidence=_decimal4(detection.confidence),
        detection_confidence=_decimal4(detection.confidence),
        box_x_norm=_decimal6(box.x),
        box_y_norm=_decimal6(box.y),
        box_w_norm=_decimal6(box.w),
        box_h_norm=_decimal6(box.h),
        width_px=width_px,
        height_px=height_px,
        area_px=area_px,
        aspect_ratio=aspect_ratio,
    )


def _decimal4(value: float) -> Decimal:
    """Clamp into [0, 1] and round to NUMERIC(5,4) scale."""
    clamped = max(0.0, min(1.0, float(value)))
    return Decimal(str(round(clamped, 4)))


def _decimal6(value: float) -> Decimal:
    """Clamp into (0, 1] and round to NUMERIC(7,6). The DB enforces
    ``box_w_norm > 0``; backends already raise ``w/h`` to ``1e-6`` minimum."""
    clamped = max(1e-6, min(1.0, float(value)))
    return Decimal(str(round(clamped, 6)))


async def _classify_all_detections(
    *,
    session: AsyncSession,
    repos: _Repos,
    router: TrafficRouter,
    pipeline: ClassifyPipeline,
    image: ScanImage,
    image_bytes: bytes,
    detect_inference: Inference,
    user_id: UUID,
    batch_id: UUID,
) -> bool:
    """Classify every detection, routing each seed-type group to its own model.

    Returns ``True`` if any group's classification failed (so the caller can
    degrade the batch to ``partial``). A seed type with no registered
    classifier is skipped (its detections stay unclassified) — that's an
    expected state, not a failure.
    """
    stmt = select(SeedDetection).where(SeedDetection.inference_id == detect_inference.id)
    detections = list((await session.execute(stmt)).scalars().all())
    if not detections:
        log.info("analyze.classify_skipped", reason="no_detections", image_id=str(image.id))
        return False

    # Group detections by their resolved seed type. ``None`` (unrecognized
    # class) can't be classified — there's no per-type model to route to.
    groups: dict[UUID, list[SeedDetection]] = {}
    for det in detections:
        if det.seed_type_id is None:
            continue
        groups.setdefault(det.seed_type_id, []).append(det)

    if not groups:
        log.info(
            "analyze.classify_skipped",
            reason="no_typed_detections",
            image_id=str(image.id),
        )
        return False

    any_failed = False
    for type_id, group in groups.items():
        try:
            classify_model = await _resolve_classify_model(
                router=router,
                models=repos.models,
                seed_type_id=type_id,
                user_id=user_id,
                batch_id=batch_id,
            )
        except Exception as exc:
            log.exception(
                "analyze.classify_resolve_failed",
                batch_id=str(batch_id),
                seed_type_id=str(type_id),
                error=repr(exc),
            )
            any_failed = True
            continue

        if classify_model is None:
            continue  # no classifier for this seed type — leave unclassified

        try:
            await _run_classify_for_detections(
                session=session,
                repos=repos,
                pipeline=pipeline,
                image=image,
                image_bytes=image_bytes,
                detections=group,
                classify_model=classify_model,
            )
        except Exception as exc:
            log.exception(
                "analyze.classify_group_failed",
                batch_id=str(batch_id),
                seed_type_id=str(type_id),
                error=repr(exc),
            )
            any_failed = True

    return any_failed


async def _run_classify_for_detections(
    *,
    session: AsyncSession,
    repos: _Repos,
    pipeline: ClassifyPipeline,
    image: ScanImage,
    image_bytes: bytes,
    detections: list[SeedDetection],
    classify_model: ModelArtifact,
) -> None:
    """Crop each detection from the image, classify it, and bulk-update
    the ``quality`` column. Classification adds a fresh ``inferences`` row
    so the registry can A/B classifiers independently of detectors.

    ``detections`` is the pre-grouped list for a single seed type — the caller
    (:func:`_classify_all_detections`) resolved ``classify_model`` to match."""
    if not detections:
        return

    classify_inference = await repos.inferences.add_inference(
        image_id=image.id,
        model_id=classify_model.id,
        backend=classify_model.backend,
        latency_ms=None,
    )

    cfg = _classification_config(classify_model)

    # PIL is happy to keep one decoded image around; we crop from it
    # rather than re-decoding the bytes per detection.
    base_img = Image.open(BytesIO(image_bytes)).convert("RGB")
    width, height = base_img.size

    updates: list[tuple[UUID, str]] = []
    total_latency_ms = 0
    valid_labels = {q.value for q in SeedQuality}

    try:
        for det in detections:
            crop_bytes = _crop_to_jpeg(base_img, det, width, height)
            outcome = await pipeline.run(
                crop=crop_bytes,
                cfg=cfg,
                backend_name=classify_model.backend,
            )
            label = outcome.classification.label
            if label not in valid_labels:
                # Defensive: a misconfigured model returning class names
                # like "ok"/"reject" would otherwise blow up the enum
                # cast. Skip the row rather than fail the batch.
                log.warning(
                    "analyze.classify_unknown_label",
                    detection_id=str(det.id),
                    label=label,
                )
                continue
            updates.append((det.id, label))
            total_latency_ms += outcome.latency_ms
    finally:
        base_img.close()

    if updates:
        await repos.detections.update_quality_many(updates)

    await session.execute(
        update(Inference)
        .where(Inference.id == classify_inference.id)
        .values(latency_ms=total_latency_ms or None)
        .execution_options(synchronize_session=False)
    )
    await session.commit()

    log.info(
        "analyze.classify_persisted",
        image_id=str(image.id),
        inference_id=str(classify_inference.id),
        n_classified=len(updates),
        n_total=len(detections),
        latency_ms_sum=total_latency_ms,
    )
    # Detect inference's detections now have ``quality`` populated; resync
    # so fact_detection rows reflect the labels. The detect inference id is the
    # one these detection rows belong to (they share it within an image).
    dispatch_after_commit(SYNC_INFERENCE, str(classify_inference.id))
    dispatch_after_commit(SYNC_DETECTIONS, str(detections[0].inference_id))


def _crop_to_jpeg(base_img: Image.Image, det: SeedDetection, width: int, height: int) -> bytes:
    """Cut a normalized bbox out of the source image and JPEG-encode it.

    Bounding boxes are normalized to [0, 1]. We multiply by the source
    image dimensions at render time (CLAUDE.md: pixel coords are derived,
    never the source of truth)."""
    x = float(det.box_x_norm) * width
    y = float(det.box_y_norm) * height
    w = float(det.box_w_norm) * width
    h = float(det.box_h_norm) * height
    # Clamp so floating drift doesn't push us off the image edge.
    left = max(0, int(x))
    top = max(0, int(y))
    right = min(width, int(x + w))
    bottom = min(height, int(y + h))
    if right <= left or bottom <= top:
        # Degenerate crop — fall back to a 1px box so PIL doesn't crash
        # and the model can still emit a "bad" label.
        right = min(width, left + 1)
        bottom = min(height, top + 1)
    crop = base_img.crop((left, top, right, bottom))
    out = BytesIO()
    crop.save(out, format="JPEG", quality=92)
    return out.getvalue()


# ── Batch finalisation ────────────────────────────────────────────────────────


async def _finalize_batch_if_done(
    *,
    session: AsyncSession,
    repos: _Repos,
    batch_id: UUID,
    started_at: datetime | None,
    had_classify_failure: bool,
) -> None:
    """Flip the batch terminal when every image has at least one detect
    inference. ``partial`` if any inference recorded an error or any image
    saw a non-fatal classify failure; otherwise ``succeeded``."""
    total_images = await repos.images.count_for_batch(batch_id)
    detect_done, any_error = await _detect_progress(session, batch_id)

    if detect_done < total_images:
        log.info(
            "analyze.batch_pending",
            batch_id=str(batch_id),
            detect_done=detect_done,
            total=total_images,
        )
        return

    duration_ms = _duration_ms(started_at)
    new_status = BatchStatus.PARTIAL if any_error or had_classify_failure else BatchStatus.SUCCEEDED
    flipped = await _mark_batch_terminal(
        repos=repos,
        batch_id=batch_id,
        new=new_status,
        duration_ms=duration_ms,
    )
    await session.commit()
    log.info(
        "analyze.batch_finished",
        batch_id=str(batch_id),
        status=new_status.value,
        duration_ms=duration_ms,
        flipped=flipped,
    )
    if flipped:
        dispatch_after_commit(SYNC_SCAN_BATCH, str(batch_id))


async def _detect_progress(session: AsyncSession, batch_id: UUID) -> tuple[int, bool]:
    """Count distinct images in this batch with a *detection* inference,
    and whether any of them recorded an error."""
    stmt = (
        select(
            func.count(func.distinct(Inference.image_id)),
            func.bool_or(Inference.error.isnot(None)),
        )
        .select_from(Inference)
        .join(ScanImage, Inference.image_id == ScanImage.id)
        .join(ModelArtifact, ModelArtifact.id == Inference.model_id)
        .where(
            ScanImage.batch_id == batch_id,
            ModelArtifact.kind == ModelKind.DETECTION.value,
        )
    )
    row = (await session.execute(stmt)).one()
    return int(row[0] or 0), bool(row[1])


def _duration_ms(started_at: datetime | None) -> int | None:
    if started_at is None:
        return None
    finished = datetime.now(tz=UTC)
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=UTC)
    return int((finished - started_at).total_seconds() * 1000)


async def _mark_batch_terminal(
    *,
    repos: _Repos,
    batch_id: UUID,
    new: BatchStatus,
    duration_ms: int | None,
) -> bool:
    """CAS running → terminal, also setting ``finished_at`` and
    ``duration_ms``. Returns True iff this caller flipped the row."""
    stmt = (
        update(ScanBatch)
        .where(
            ScanBatch.id == batch_id,
            ScanBatch.status == BatchStatus.RUNNING.value,
        )
        .values(
            status=new.value,
            finished_at=func.now(),
            duration_ms=duration_ms,
        )
        .execution_options(synchronize_session=False)
    )
    result = await repos.batches.session.execute(stmt)
    return (result.rowcount or 0) == 1  # type: ignore[attr-defined]


async def _mark_batch_failed(
    *,
    repos: _Repos,
    batch_id: UUID,
    started_at: datetime | None,
    error_message: str | None = None,
) -> None:
    """Best-effort transition to ``failed``. Used when detect itself
    crashes; classify failures use ``partial`` via the normal finaliser.

    ``error_message`` is surfaced to clients via ``BatchDetailOut`` so the web
    and mobile apps can explain *why* a scan failed (e.g. no detection model is
    configured) instead of showing a blank failure."""
    duration_ms = _duration_ms(started_at)
    values: dict[str, object] = {
        "status": BatchStatus.FAILED.value,
        "finished_at": func.now(),
        "duration_ms": duration_ms,
    }
    if error_message is not None:
        values["error_message"] = error_message
    stmt = (
        update(ScanBatch)
        .where(
            ScanBatch.id == batch_id,
            ScanBatch.status.in_((BatchStatus.PENDING.value, BatchStatus.RUNNING.value)),
        )
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    await repos.batches.session.execute(stmt)


__all__ = ["analyze_image"]
