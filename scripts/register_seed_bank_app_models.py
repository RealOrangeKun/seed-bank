"""Register the new two-stage + YOLO models from the standalone desktop app.

Replaces the three legacy artifacts (combined Faster R-CNN, ResNet18 coffee,
ResNet18 maize) with the full set shipped in ``seed-bank-app/weights``:

* **Stage-1 detector** — ``faster-rcnn-resnet50-pan-v1`` (20 superclasses),
  backend ``torch_local``, with the ``class_map`` baked into its config so the
  worker can route each crop to a specialist.
* **YOLO one-shot detector** — ``best_YOLO11M.pt``, backend ``yolo``. A
  selectable alternative to the two-stage path (one model, 40 fine classes).
* **10 EfficientNet-B2 specialists** — one per seed type that has a trained
  Stage-2 checkpoint, backend ``torch_local``, each carrying its ordered
  ``classes`` + ``segment=true`` (U2NET background removal) in config.

Idempotency: re-running re-uploads weights (same MinIO key) and registers a new
artifact row each time, so run once per environment. Use ``--promote`` to flip
everything to ``production`` after upload.

Usage::

    python -m scripts.register_seed_bank_app_models \
        --weights-dir seed-bank-app/weights --promote
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from seedbank.core.config import get_settings
from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.enums import ModelBackend, ModelKind, ModelStatus
from seedbank.infrastructure.db.models import SeedType
from seedbank.infrastructure.db.repositories import ModelArtifactRepository
from seedbank.infrastructure.ml.seed_taxonomy import (
    CLASS_MAP,
    DETECTOR_BUILDER_KEY,
    SPECIALISTS,
)
from seedbank.services.model_registry_service import (
    ModelRegistryService,
    RegisterModelInput,
)

log = get_logger("seedbank.register_seed_bank_app_models")

# Specialist seed-type code → weights path (relative to --weights-dir). The
# filesystem layout is app-specific, so it lives here rather than the taxonomy.
_SPECIALIST_WEIGHTS: dict[str, str] = {
    "maize": "checkpoints_maize/bestV17_MAIZE.pt",
    "soybean": "checkpoints_soybean/bestV12_SOYBEAN.pt",
    "garlic": "checkpoints_garlic/best_garlic.pt",
    "black_channa": "checkpoints_BlackChanna/best_BlackChanna.pt",
    "black_pepper": "checkpoints_BlackPepper/best_BLACK_PEPPER.pt",
    "green_matar": "checkpoints_GreenMatar/best_GreenMatar.pt",
    "kabuli_channa": "checkpoints_KabuliChanna/best_KABULI_CHANNA.pt",
    "rice_paddy": "checkpoints_RicePaddy/best_RicePaddy.pt",
    "wheat_grain": "checkpoints_WheatGrain/best_WheatGrain.pt",
    "white_matar": "checkpoints_WhiteMatar/best_WhiteMatar.pt",
}

_DETECTOR_WEIGHTS = "fasterRCNN/FasterRcnn_Finale_V1.pth"
_YOLO_WEIGHTS = "YOLOv11M/best_YOLO11M.pt"


@dataclass(frozen=True, slots=True)
class _Plan:
    name: str
    version: str
    kind: ModelKind
    backend: ModelBackend
    builder_key: str
    weights_rel: str
    seed_type_code: str | None
    config: dict[str, object]


def _build_plans() -> list[_Plan]:
    plans: list[_Plan] = [
        _Plan(
            name="Faster R-CNN ResNet50-PAN Superclass Detector",
            version="v1",
            kind=ModelKind.DETECTION,
            backend=ModelBackend.TORCH_LOCAL,
            builder_key=DETECTOR_BUILDER_KEY,
            weights_rel=_DETECTOR_WEIGHTS,
            seed_type_code=None,
            config={
                "builder_key": DETECTOR_BUILDER_KEY,
                "confidence_threshold": 0.5,
                # Low NMS IoU: seeds are densely packed, so aggressively dedupe
                # overlapping boxes on the same seed (applied to roi_heads.nms_thresh).
                "iou_threshold": 0.1,
                "image_size": 448,
                "two_stage": True,
                # JSON object keys must be strings.
                "class_map": {str(k): v for k, v in CLASS_MAP.items()},
            },
        ),
        _Plan(
            name="YOLOv11M One-Shot Seed Detector",
            version="v1",
            kind=ModelKind.DETECTION,
            backend=ModelBackend.YOLO,
            builder_key="yolo",  # ignored by the ultralytics backend
            weights_rel=_YOLO_WEIGHTS,
            seed_type_code=None,
            # Low NMS IoU (0.1) to dedupe overlapping boxes on densely packed seeds.
            config={"confidence_threshold": 0.8, "iou_threshold": 0.1, "image_size": 640},
        ),
    ]
    for spec in SPECIALISTS:
        weights_rel = _SPECIALIST_WEIGHTS[spec.code]
        plans.append(
            _Plan(
                name=f"EfficientNet-B2 CBAM Specialist ({spec.code})",
                version="v1",
                kind=ModelKind.CLASSIFICATION,
                backend=ModelBackend.TORCH_LOCAL,
                builder_key=spec.builder_key,
                weights_rel=weights_rel,
                seed_type_code=spec.code,
                config={
                    "builder_key": spec.builder_key,
                    "threshold": spec.threshold,
                    "image_size": spec.image_size,
                    "segment": spec.segment,
                    "classes": list(spec.classes),
                },
            )
        )
    return plans


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--weights-dir",
        type=Path,
        default=Path("seed-bank-app/weights"),
        help="Directory containing the standalone app's weights tree.",
    )
    p.add_argument(
        "--promote",
        action="store_true",
        help="Flip every registered model to 'production' after upload.",
    )
    p.add_argument("--actor-id", default=None, help="UUID of the AI developer (audit_log).")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the plan + weight files without touching MinIO/DB.",
    )
    return p.parse_args()


async def _resolve_seed_type_id(session: AsyncSession, code: str | None) -> UUID | None:
    if code is None:
        return None
    row = (
        await session.execute(select(SeedType).where(SeedType.code == code))
    ).scalar_one_or_none()
    if row is None:
        raise SystemExit(f"Seed type {code!r} not found. Run `python -m scripts.seed_dev` first.")
    return row.id


async def _run(args: argparse.Namespace) -> int:
    weights_dir: Path = args.weights_dir
    plans = _build_plans()

    # Validate every weights file exists before doing anything stateful.
    missing = [p.weights_rel for p in plans if not (weights_dir / p.weights_rel).is_file()]
    if missing:
        print(f"missing weight files under {weights_dir}:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 2

    print(f"Planned {len(plans)} models from {weights_dir}:")
    for p in plans:
        size_mb = (weights_dir / p.weights_rel).stat().st_size / 1e6
        print(f"  • {p.name:52s} [{p.kind.value:14s} {p.backend.value:11s}] {size_mb:7.1f} MB")
    if args.dry_run:
        print("dry-run: nothing uploaded.")
        return 0

    settings = get_settings()
    from seedbank.infrastructure.storage import get_storage

    storage = get_storage()
    bucket = settings.minio_bucket_models
    await storage.ensure_bucket(bucket)

    engine = create_async_engine(str(settings.postgres_dsn), future=True)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    actor_id = (args.actor_id and UUID(args.actor_id)) or uuid4()
    registered: list[UUID] = []
    try:
        async with sm() as session:
            svc = ModelRegistryService(
                session=session,
                models=ModelArtifactRepository(session),
                storage=storage,
                settings=settings,
            )
            for plan in plans:
                seed_type_id = await _resolve_seed_type_id(session, plan.seed_type_code)
                key = f"{plan.builder_key}/{plan.version}/{Path(plan.weights_rel).name}"
                artifact_uri = f"s3://{bucket}/{key}"
                data = (weights_dir / plan.weights_rel).read_bytes()
                await storage.put_object(bucket, key, data, "application/octet-stream")
                row = await svc.register(
                    actor_id=actor_id,
                    payload=RegisterModelInput(
                        name=plan.name,
                        version=plan.version,
                        kind=plan.kind,
                        backend=plan.backend,
                        artifact_uri=artifact_uri,
                        seed_type_id=seed_type_id,
                        config=plan.config,
                        training_metadata={"source": "seed-bank-app"},
                    ),
                )
                registered.append(row.id)
                print(f"  registered {row.id} ({plan.name})")

            if args.promote:
                for model_id in registered:
                    await svc.change_status(
                        actor_id=actor_id,
                        model_id=model_id,
                        new_status=ModelStatus.PRODUCTION,
                    )
                print(f"promoted {len(registered)} models → production")
    finally:
        await engine.dispose()
    print(f"done: {len(registered)} models registered.")
    return 0


def main() -> int:
    return asyncio.run(_run(_parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
