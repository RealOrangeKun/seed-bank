"""Swap in the new detection weights (Faster R-CNN V4 + YOLOv8) only.

The 10 EfficientNet-B2 specialists are already registered and ``production`` with
unchanged weights, so this script deliberately leaves them alone (re-registering
them would create a second ``production`` row per segment and break
``ModelArtifactRepository.get_production``, which expects exactly one).

It:

1. uploads the two new detector weight files to MinIO,
2. registers the Faster R-CNN V4 two-stage detector and promotes it to
   ``production`` (``change_status`` auto-archives the incumbent v1 detector),
3. registers the YOLOv8 one-shot detector at ``staging`` — it must NOT be
   ``production`` or it collides with the Faster R-CNN in ``get_production``;
   the analyze ``mode=fast`` path reaches a staging YOLO via
   ``find_detection_by_backend``,
4. archives any other non-archived detection model (the deleted YOLOv11 row, the
   old v1 Faster R-CNN if it wasn't auto-archived).

Run inside the worker-inference container (weights mounted at ``/weights``)::

    python -m scripts.swap_detector_weights --weights-dir /weights
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from seedbank.core.config import get_settings
from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.enums import ModelBackend, ModelKind, ModelStatus
from seedbank.infrastructure.db.repositories import ModelArtifactRepository
from seedbank.services.model_registry_service import ModelRegistryService, RegisterModelInput

log = get_logger("seedbank.swap_detector_weights")

_FRCNN_BUILDER_KEY = "faster-rcnn-resnet50-pan-v4"
_FRCNN_WEIGHTS = "fasterRCNN/Resnet50FPN_PANet_CIoU_ROI_V4.pth"
# class id -> catalog seed_types.code, confirmed by the trainer (RCNN_CLASS_MAP).
# coffee has no Stage-2 specialist, so coffee crops grade good by the default rule.
_FRCNN_CLASS_MAP = {"1": "coffee", "2": "maize", "3": "black_pepper", "4": "garlic"}
_FRCNN_CONFIG: dict[str, object] = {
    "builder_key": _FRCNN_BUILDER_KEY,
    "confidence_threshold": 0.6,  # RCNN_CONF_THRESH
    "iou_threshold": 0.5,  # RCNN_NMS_IOU_THRESH
    "image_size": 448,
    "two_stage": True,
    "class_map": _FRCNN_CLASS_MAP,
}

_YOLO_WEIGHTS = "YOLOV8/yolo-v8-finale-v2.pt"
_YOLO_CONFIG: dict[str, object] = {
    "confidence_threshold": 0.5,  # YOLO_CONF_THRESH
    "iou_threshold": 0.8,  # YOLO_NMS_IOU_THRESH
    "image_size": 640,
}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--weights-dir", type=Path, default=Path("/weights"))
    p.add_argument("--actor-id", default=None, help="UUID of the AI developer (audit_log).")
    return p.parse_args()


async def _register(
    svc: ModelRegistryService,
    storage: object,
    bucket: str,
    *,
    actor_id: UUID,
    weights_path: Path,
    builder_key: str,
    version: str,
    name: str,
    backend: ModelBackend,
    config: dict[str, object],
) -> UUID:
    key = f"{builder_key}/{version}/{weights_path.name}"
    await storage.put_object(  # type: ignore[attr-defined]
        bucket, key, weights_path.read_bytes(), "application/octet-stream"
    )
    # Idempotent: reuse a previously-registered row for this name+version rather
    # than piling up duplicates on a re-run.
    existing = await svc.models.find_by_name_version(name, version)
    if existing is not None and existing.status != ModelStatus.ARCHIVED.value:
        print(f"  reusing {existing.id}  ({name}, status={existing.status})")
        return existing.id
    row = await svc.register(
        actor_id=actor_id,
        payload=RegisterModelInput(
            name=name,
            version=version,
            kind=ModelKind.DETECTION,
            backend=backend,
            artifact_uri=f"s3://{bucket}/{key}",
            seed_type_id=None,
            config=config,
            training_metadata={"source": "seed-bank-app", "detector_swap": True},
        ),
    )
    print(f"  registered {row.id}  ({name})")
    return row.id


async def _ensure_status(
    svc: ModelRegistryService, *, actor_id: UUID, model_id: UUID, target: ModelStatus
) -> None:
    """Walk the registered → staging → production ladder up to ``target``."""
    ladder = [ModelStatus.REGISTERED, ModelStatus.STAGING, ModelStatus.PRODUCTION]
    row = await svc.models.get(model_id)
    assert row is not None
    current = ModelStatus(row.status)
    if current is ModelStatus.ARCHIVED or current not in ladder or target not in ladder:
        if current is not target:
            await svc.change_status(actor_id=actor_id, model_id=model_id, new_status=target)
        return
    for step in ladder[ladder.index(current) + 1 : ladder.index(target) + 1]:
        await svc.change_status(actor_id=actor_id, model_id=model_id, new_status=step)


async def _run(args: argparse.Namespace) -> int:
    weights_dir: Path = args.weights_dir
    frcnn_path = weights_dir / _FRCNN_WEIGHTS
    yolo_path = weights_dir / _YOLO_WEIGHTS
    missing = [str(p) for p in (frcnn_path, yolo_path) if not p.is_file()]
    if missing:
        for m in missing:
            print(f"missing weight file: {m}")
        return 2

    settings = get_settings()
    from seedbank.infrastructure.storage import get_storage

    storage = get_storage()
    bucket = settings.minio_bucket_models
    await storage.ensure_bucket(bucket)

    engine = create_async_engine(str(settings.postgres_dsn), future=True)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    actor_id = (args.actor_id and UUID(args.actor_id)) or uuid4()
    try:
        async with sm() as session:
            svc = ModelRegistryService(
                session=session,
                models=ModelArtifactRepository(session),
                storage=storage,
                settings=settings,
            )

            frcnn_id = await _register(
                svc,
                storage,
                bucket,
                actor_id=actor_id,
                weights_path=frcnn_path,
                builder_key=_FRCNN_BUILDER_KEY,
                version="v4",
                name="Faster R-CNN ResNet50-PAN V4 Detector",
                backend=ModelBackend.TORCH_LOCAL,
                config=_FRCNN_CONFIG,
            )
            yolo_id = await _register(
                svc,
                storage,
                bucket,
                actor_id=actor_id,
                weights_path=yolo_path,
                builder_key="yolo",
                version="v2",
                name="YOLOv8 One-Shot Seed Detector",
                backend=ModelBackend.YOLO,
                config=_YOLO_CONFIG,
            )

            # YOLO must reach staging first so that, when we promote the Faster
            # R-CNN, the YOLO is reachable via mode=fast but is NOT a second
            # production detection row (get_production expects exactly one).
            await _ensure_status(
                svc, actor_id=actor_id, model_id=yolo_id, target=ModelStatus.STAGING
            )
            print(f"set YOLOv8 → staging ({yolo_id})")

            # Promote the Faster R-CNN to production via staging (auto-archives
            # the incumbent detection production row in the same txn).
            await _ensure_status(
                svc, actor_id=actor_id, model_id=frcnn_id, target=ModelStatus.PRODUCTION
            )
            print(f"promoted Faster R-CNN V4 → production ({frcnn_id})")

            # Archive any other non-archived detection rows (old YOLOv11, stale v1).
            keep = {frcnn_id, yolo_id}
            active = await ModelArtifactRepository(session).list_active()
            for row in active:
                if row.kind == ModelKind.DETECTION.value and row.id not in keep:
                    await svc.change_status(
                        actor_id=actor_id, model_id=row.id, new_status=ModelStatus.ARCHIVED
                    )
                    print(f"archived old detector {row.id} ({row.name} {row.version})")
    finally:
        await engine.dispose()
    print("done.")
    return 0


def main() -> int:
    return asyncio.run(_run(_parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
