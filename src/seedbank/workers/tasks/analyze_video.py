"""``seedbank.analyze_video`` — analyze a video *as a video*.

The API stores the raw video in MinIO, commits a ``scan_batch`` (``pending``),
and dispatches this task. It then:

1. resolves the promoted **YOLO** detector (video is YOLO-only),
2. runs YOLO over the clip's frames (Ultralytics ``predict``) and burns the
   detection boxes into each frame (``Results.plot()``),
3. re-encodes the annotated frames to a browser/iOS-playable **H.264 mp4**
   (via imageio-ffmpeg — OpenCV's bundled FFmpeg can't encode H.264) and stores
   it as the batch's ``result_video_key``,
4. persists a poster ``scan_image`` + one ``inference`` + the detections from a
   sampled subset of frames so the good/bad stats and full
   ``detection → inference → model`` traceability still hold,
5. flips the batch terminal (``succeeded`` / ``failed``).

Unlike the image path there is no per-image fan-out: one task owns the whole
clip so it can draw + encode in a single streaming pass (bounded memory).
"""

from __future__ import annotations

import hashlib
import math
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from seedbank.core.config import get_settings
from seedbank.core.exceptions import ExternalServiceError, ModelNotReadyError, NotFoundError
from seedbank.core.ids import uuid7
from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.enums import BatchStatus, ModelBackend
from seedbank.infrastructure.db.models import ModelArtifact, ScanBatch, ScanImage
from seedbank.infrastructure.db.repositories import (
    InferenceRepository,
    ModelArtifactRepository,
    ScanBatchRepository,
    ScanImageRepository,
    SeedDetectionRepository,
    SeedTypeRepository,
)
from seedbank.infrastructure.ml.backends.base import BoundingBox, Detection
from seedbank.infrastructure.ml.pipeline.factory import get_model_manager
from seedbank.infrastructure.ml.yolo_taxonomy import classify_name
from seedbank.infrastructure.storage import get_storage
from seedbank.workers.celery_app import celery_app
from seedbank.workers.runtime import run_async
from seedbank.workers.session import worker_session_scope
from seedbank.workers.tasks.analyze import (
    _build_seed_detection,
    _duration_ms,
    _mark_batch_failed,
    _mark_batch_terminal,
    _Repos,
)
from seedbank.workers.tasks.dwh import (
    SYNC_DETECTIONS,
    SYNC_INFERENCE,
    SYNC_SCAN_BATCH,
    dispatch_after_commit,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from seedbank.core.config import Settings
    from seedbank.infrastructure.storage import MinioStorage

log = get_logger(__name__)

_NO_YOLO_MESSAGE = (
    "No YOLO detector is available. Video analysis requires a promoted YOLO "
    "model — an administrator must register and promote one."
)


@dataclass(slots=True)
class _AnnotateResult:
    video_mp4: bytes
    poster_jpeg: bytes
    width: int
    height: int
    frame_count: int
    detections: list[Detection]


@celery_app.task(  # type: ignore[untyped-decorator]
    name="seedbank.analyze_video",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    autoretry_for=(ExternalServiceError,),
)
def analyze_video(
    self: object,  # noqa: ARG001 — Celery requires `bind=True` to accept self
    batch_id: str,
    video_storage_key: str,
    video_content_type: str,  # noqa: ARG001 — kept for traceability / future use
) -> None:
    """Sync Celery wrapper. The real work lives in the async coroutine."""
    run_async(
        _async_analyze_video(
            batch_id=UUID(batch_id),
            video_storage_key=video_storage_key,
        )
    )


async def _async_analyze_video(*, batch_id: UUID, video_storage_key: str) -> None:
    settings = get_settings()
    storage = get_storage()
    async with worker_session_scope() as session:
        repos = _Repos(
            batches=ScanBatchRepository(session),
            images=ScanImageRepository(session),
            models=ModelArtifactRepository(session),
            inferences=InferenceRepository(session),
            detections=SeedDetectionRepository(session),
            seed_types=SeedTypeRepository(session),
        )

        batch = await repos.batches.get(batch_id)
        if batch is None:
            raise NotFoundError(f"scan_batch {batch_id} not found")
        # Idempotency: a retry after we've already started is a no-op.
        if batch.status != BatchStatus.PENDING.value:
            log.info("analyze_video.skip", batch_id=str(batch_id), status=batch.status)
            return

        cas = await repos.batches.cas_status(
            batch_id,
            expected=BatchStatus.PENDING,
            new=BatchStatus.RUNNING,
            set_started_at=True,
        )
        await session.commit()
        started_at = cas.started_at

        # Resolve the YOLO detector — video is YOLO-only.
        detect_model = await repos.models.find_detection_by_backend(ModelBackend.YOLO)
        if detect_model is None:
            await _mark_batch_failed(
                repos=repos,
                batch_id=batch_id,
                started_at=started_at,
                error_message=_NO_YOLO_MESSAGE,
            )
            await session.commit()
            dispatch_after_commit(SYNC_SCAN_BATCH, str(batch_id))
            raise ModelNotReadyError(_NO_YOLO_MESSAGE)

        # Pull the raw video (retryable on MinIO failure via autoretry_for).
        video_bytes = await storage.get_object(settings.minio_bucket_images, video_storage_key)

        cfg = detect_model.config or {}
        yolo = await get_model_manager().load_yolo(detect_model.id, detect_model.artifact_uri)

        # Ultralytics decides image-vs-video by file extension, so the temp file
        # must keep the real container suffix (the storage key carries it).
        suffix = Path(video_storage_key).suffix or ".mp4"

        try:
            result = await _annotate_video_async(
                yolo,
                video_bytes,
                suffix=suffix,
                conf=float(cfg.get("confidence_threshold", 0.5)),
                iou=float(cfg.get("iou_threshold", 0.7)),
                imgsz=int(cfg.get("image_size", 640)),
                max_frames=settings.analyze_video_max_frames,
                max_stats_frames=settings.analyze_video_max_stats_frames,
            )
        except ExternalServiceError:
            raise  # MinIO/network hiccup — let Celery retry.
        except Exception:
            log.exception("analyze_video.annotate_failed", batch_id=str(batch_id))
            await _mark_batch_failed(
                repos=repos,
                batch_id=batch_id,
                started_at=started_at,
                error_message="Video analysis failed while processing the clip.",
            )
            await session.commit()
            dispatch_after_commit(SYNC_SCAN_BATCH, str(batch_id))
            raise

        if result is None or result.frame_count == 0:
            await _mark_batch_failed(
                repos=repos,
                batch_id=batch_id,
                started_at=started_at,
                error_message=(
                    "Could not read any frames from the uploaded video. Please "
                    "try a different file or format (mp4 recommended)."
                ),
            )
            await session.commit()
            dispatch_after_commit(SYNC_SCAN_BATCH, str(batch_id))
            log.warning("analyze_video.no_frames", batch_id=str(batch_id))
            return

        await _store_and_finalize(
            session=session,
            repos=repos,
            storage=storage,
            settings=settings,
            batch=batch,
            detect_model=detect_model,
            batch_id=batch_id,
            started_at=started_at,
            result=result,
        )


async def _store_and_finalize(
    *,
    session: AsyncSession,
    repos: _Repos,
    storage: MinioStorage,
    settings: Settings,
    batch: ScanBatch,
    detect_model: ModelArtifact,
    batch_id: UUID,
    started_at: datetime | None,
    result: _AnnotateResult,
) -> None:
    """Upload the annotated video + poster, persist the detection graph, and
    flip the batch ``succeeded``."""
    bucket = settings.minio_bucket_images
    video_key = f"batches/{batch_id}/annotated.mp4"
    await storage.put_object(bucket, video_key, result.video_mp4, "video/mp4")
    image_id = uuid7()
    poster_key = f"batches/{batch_id}/{image_id}.jpg"
    await storage.put_object(bucket, poster_key, result.poster_jpeg, "image/jpeg")

    image = ScanImage(
        id=image_id,
        batch_id=batch_id,
        storage_key=poster_key,
        content_type="image/jpeg",
        size_bytes=len(result.poster_jpeg),
        sha256=hashlib.sha256(result.poster_jpeg).hexdigest(),
        width=result.width,
        height=result.height,
    )
    await repos.images.add(image)
    inference = await repos.inferences.add_inference(
        image_id=image.id,
        model_id=detect_model.id,
        backend=detect_model.backend,
        latency_ms=None,
    )
    code_to_id = await repos.seed_types.code_to_id()
    rows = []
    for det in result.detections:
        code, quality = classify_name(det.class_name)
        rows.append(
            _build_seed_detection(
                inference_id=inference.id,
                seed_type_id=code_to_id.get(code) if code else None,
                detection=det,
                image=image,
                quality=quality,
            )
        )
    await repos.detections.add_many(rows)

    batch.result_video_key = video_key
    await _mark_batch_terminal(
        repos=repos,
        batch_id=batch_id,
        new=BatchStatus.SUCCEEDED,
        duration_ms=_duration_ms(started_at),
    )
    await session.commit()

    dispatch_after_commit(SYNC_INFERENCE, str(inference.id))
    dispatch_after_commit(SYNC_DETECTIONS, str(inference.id))
    dispatch_after_commit(SYNC_SCAN_BATCH, str(batch_id))
    log.info(
        "analyze_video.done",
        batch_id=str(batch_id),
        frames=result.frame_count,
        n_detections=len(rows),
    )


async def _annotate_video_async(
    yolo: object,
    video_bytes: bytes,
    *,
    suffix: str = ".mp4",
    conf: float,
    iou: float,
    imgsz: int,
    max_frames: int,
    max_stats_frames: int,
) -> _AnnotateResult | None:
    import asyncio

    return await asyncio.to_thread(
        _annotate_video,
        yolo,
        video_bytes,
        suffix=suffix,
        conf=conf,
        iou=iou,
        imgsz=imgsz,
        max_frames=max_frames,
        max_stats_frames=max_stats_frames,
    )


def _annotate_video(
    yolo: object,
    video_bytes: bytes,
    *,
    suffix: str = ".mp4",
    conf: float,
    iou: float,
    imgsz: int,
    max_frames: int,
    max_stats_frames: int,
) -> _AnnotateResult | None:
    """Run YOLO over the clip, draw boxes per frame, encode an H.264 mp4.

    Streaming (one frame in memory at a time) so a long clip doesn't blow up RAM.
    Returns ``None`` when the video can't be opened/decoded.
    """
    import cv2
    import imageio.v2 as imageio

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp_in:
        tmp_in.write(video_bytes)
        in_path = tmp_in.name
    out_path = str(Path(in_path).with_suffix(".out.mp4"))
    try:
        cap = cv2.VideoCapture(in_path)
        try:
            if not cap.isOpened():
                return None
            src_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        finally:
            cap.release()

        # Stride so YOLO runs on at most ``max_frames`` frames but the annotated
        # video still spans the whole clip.
        vid_stride = max(1, math.ceil(total / max_frames)) if total > 0 else 1
        out_fps = max(1.0, (src_fps / vid_stride) if src_fps > 0 else 12.0)
        # Persist detections from at most ``max_stats_frames`` processed frames.
        processed_estimate = math.ceil(total / vid_stride) if total > 0 else max_stats_frames
        stats_stride = max(1, math.ceil(processed_estimate / max_stats_frames))

        results = yolo.predict(  # type: ignore[attr-defined]
            source=in_path,
            stream=True,
            conf=conf,
            iou=iou,
            imgsz=imgsz,
            vid_stride=vid_stride,
            verbose=False,
        )

        writer = imageio.get_writer(
            out_path,
            format="FFMPEG",
            mode="I",
            fps=out_fps,
            codec="libx264",
            macro_block_size=16,  # pad to even dims (libx264 + yuv420p need it)
            ffmpeg_params=["-pix_fmt", "yuv420p"],
        )
        poster_jpeg: bytes | None = None
        width = height = 0
        frame_count = 0
        detections: list[Detection] = []
        try:
            for idx, r in enumerate(results):
                annotated_bgr = r.plot()  # H×W×3 BGR uint8, boxes + labels drawn
                height, width = annotated_bgr.shape[:2]
                writer.append_data(annotated_bgr[:, :, ::-1])  # BGR → RGB
                if poster_jpeg is None:
                    ok, buf = cv2.imencode(".jpg", annotated_bgr)
                    if ok:
                        poster_jpeg = buf.tobytes()
                if idx % stats_stride == 0:
                    detections.extend(_detections_from_result(r))
                frame_count += 1
        finally:
            writer.close()

        if frame_count == 0 or poster_jpeg is None:
            return None
        video_mp4 = Path(out_path).read_bytes()
        return _AnnotateResult(
            video_mp4=video_mp4,
            poster_jpeg=poster_jpeg,
            width=width,
            height=height,
            frame_count=frame_count,
            detections=detections,
        )
    finally:
        for p in (in_path, out_path):
            with suppress(OSError):
                Path(p).unlink(missing_ok=True)


def _detections_from_result(r: object) -> list[Detection]:
    """Convert one Ultralytics ``Results`` into framework-free ``Detection`` DTOs
    (normalized bbox), mirroring the YOLO backend's pixel→[0,1] mapping."""
    boxes = getattr(r, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return []
    names = getattr(r, "names", {}) or {}
    h, w = r.orig_shape  # type: ignore[attr-defined]
    xyxy = boxes.xyxy.cpu().numpy()
    scores = boxes.conf.cpu().numpy()
    labels = boxes.cls.cpu().numpy().astype(int)
    out: list[Detection] = []
    for box, score, label in zip(xyxy, scores, labels, strict=True):
        x1, y1, x2, y2 = (float(v) for v in box.tolist())
        out.append(
            Detection(
                bbox=BoundingBox(
                    x=max(0.0, x1 / w),
                    y=max(0.0, y1 / h),
                    w=min(1.0, max((x2 - x1) / w, 1e-6)),
                    h=min(1.0, max((y2 - y1) / h, 1e-6)),
                ),
                class_id=int(label),
                class_name=names.get(int(label)),
                confidence=float(score),
            )
        )
    return out


__all__ = ["analyze_video"]
