"""CLI: register a model artifact (upload weights + create DB row).

Usage::

    python scripts/register_model.py upload \
        --weights path/to/ResNet18_coffee_v3.pth \
        --key resnet18-cbam-coffee-v3 \
        --kind classification \
        --seed-type coffee \
        --version v3 \
        --name "ResNet18 CBAM Coffee Quality" \
        --backend torch_local

The script runs **directly against the service layer** (no HTTP) so it can
be invoked from the CI worker image without needing an admin API key. This
is the simpler path the spec asked us to pick.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from seedbank.core.config import get_settings
from seedbank.infrastructure.db.enums import ModelBackend, ModelKind, ModelStatus
from seedbank.infrastructure.db.models import SeedType
from seedbank.infrastructure.db.repositories import ModelArtifactRepository
from seedbank.infrastructure.ml.registry import get_builder
from seedbank.infrastructure.storage import get_storage
from seedbank.services.model_registry_service import (
    ModelRegistryService,
    RegisterModelInput,
)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    up = sub.add_parser("upload", help="Upload weights and register the model.")
    up.add_argument("--weights", required=True, type=Path)
    up.add_argument("--key", required=True, help="Builder key (e.g. resnet18-cbam-coffee-v3)")
    up.add_argument("--kind", required=True, choices=[k.value for k in ModelKind])
    up.add_argument(
        "--seed-type",
        default=None,
        help="Seed type code (e.g. coffee/maize/lentil), or omit/'none' for detection models.",
    )
    up.add_argument("--version", required=True)
    up.add_argument("--name", default=None, help="Display name; defaults to the builder key.")
    up.add_argument(
        "--backend",
        default=ModelBackend.TORCH_LOCAL.value,
        choices=[b.value for b in ModelBackend],
    )
    up.add_argument("--threshold", type=float, default=0.5)
    up.add_argument("--image-size", type=int, default=None)
    up.add_argument("--mlflow-run-id", default=None)
    up.add_argument("--metadata", default=None, help="JSON string with extra training metadata.")
    up.add_argument(
        "--actor-id",
        default=None,
        help="UUID of the AI developer running this command (for audit_log).",
    )

    promote = sub.add_parser("promote", help="Change status of an existing model.")
    promote.add_argument("--model-id", required=True, type=UUID)
    promote.add_argument(
        "--to", required=True, choices=[s.value for s in ModelStatus], dest="to_status"
    )
    promote.add_argument("--actor-id", default=None)

    return p.parse_args()


async def _resolve_seed_type_id(session: AsyncSession, code: str | None) -> UUID | None:
    if code is None or code.lower() == "none":
        return None
    stmt = select(SeedType).where(SeedType.code == code)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise SystemExit(f"Seed type code {code!r} not found in seed_types.")
    return row.id


async def _cmd_upload(args: argparse.Namespace) -> int:
    settings = get_settings()
    weights_path: Path = args.weights
    if not weights_path.is_file():
        print(f"weights file does not exist: {weights_path}", file=sys.stderr)
        return 2

    # Validate the builder key exists *before* uploading bytes.
    if args.backend == ModelBackend.TORCH_LOCAL.value:
        get_builder(args.key)  # raises BuilderNotFoundError if unknown

    storage = get_storage()
    bucket = settings.minio_bucket_models
    key = f"{args.key}/{args.version}/weights.pth"
    artifact_uri = f"s3://{bucket}/{key}"

    # Upload (blocking read; the file should be small enough — these are
    # ResNet18 weights, ~50MB).
    data = weights_path.read_bytes()
    await storage.ensure_bucket(bucket)
    await storage.put_object(bucket, key, data, "application/octet-stream")
    print(f"uploaded {len(data)} bytes to {artifact_uri}")

    engine = create_async_engine(str(settings.postgres_dsn), future=True)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with sm() as session:
            seed_type_id = await _resolve_seed_type_id(session, args.seed_type)

            extra: dict[str, object] = {}
            if args.metadata:
                extra.update(json.loads(args.metadata))

            config: dict[str, object] = {"builder_key": args.key, "threshold": args.threshold}
            if args.image_size is not None:
                config["image_size"] = args.image_size

            svc = ModelRegistryService(
                session=session,
                models=ModelArtifactRepository(session),
                storage=storage,
                settings=settings,
            )
            actor_id = args.actor_id and UUID(args.actor_id) or uuid4()  # best-effort
            row = await svc.register(
                actor_id=actor_id,
                payload=RegisterModelInput(
                    name=args.name or args.key,
                    version=args.version,
                    kind=ModelKind(args.kind),
                    backend=ModelBackend(args.backend),
                    artifact_uri=artifact_uri,
                    seed_type_id=seed_type_id,
                    config=config,
                    training_metadata=extra or None,
                    mlflow_run_id=args.mlflow_run_id,
                ),
            )
            print(f"registered model {row.id} ({row.name}:{row.version})")
    finally:
        await engine.dispose()
    return 0


async def _cmd_promote(args: argparse.Namespace) -> int:
    settings = get_settings()
    storage = get_storage()
    engine = create_async_engine(str(settings.postgres_dsn), future=True)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with sm() as session:
            svc = ModelRegistryService(
                session=session,
                models=ModelArtifactRepository(session),
                storage=storage,
                settings=settings,
            )
            actor_id = args.actor_id and UUID(args.actor_id) or uuid4()
            row = await svc.change_status(
                actor_id=actor_id,
                model_id=args.model_id,
                new_status=ModelStatus(args.to_status),
            )
            print(f"model {row.id} → {row.status}")
    finally:
        await engine.dispose()
    return 0


def main() -> int:
    args = _parse_args()
    if args.cmd == "upload":
        return asyncio.run(_cmd_upload(args))
    if args.cmd == "promote":
        return asyncio.run(_cmd_promote(args))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
