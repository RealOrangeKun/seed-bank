"""Provision the smoke pipeline fixture: a tiny, untrained detection model.

Generates seed-fixed random weights for the ``tiny-detector-smoke-v1`` builder,
uploads them to the models bucket, registers a ``model_artifacts`` row, and
promotes it to **global production** (``seed_type_id = NULL``) so
:meth:`ModelResolver.select_model` resolves a detector for every scan.

This is the seed-bank analogue of HuggingFace's ``tiny-random-*`` fixtures —
it exists purely to let the ``smoke`` workflow exercise the *real* inference
pipeline (worker image → MinIO fetch → ``load_state_dict`` → detect → persist)
without shipping production weights. It is **CI/dev only**; never run it against
a real deployment. Idempotent: a no-op if a global production detector already
exists.

Must run inside the inference worker — torch + the builder live in the
``[inference]`` extra and the API image cannot import them::

    docker compose exec worker-inference python -m scripts.provision_smoke_model
    # or, from the repo root:
    make provision-smoke-model
"""

from __future__ import annotations

import asyncio
import io
import sys

import torch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from seedbank.core.config import get_settings
from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.enums import (
    ModelBackend,
    ModelKind,
    ModelStatus,
    UserRole,
)
from seedbank.infrastructure.db.models import User
from seedbank.infrastructure.db.repositories import ModelArtifactRepository
from seedbank.infrastructure.ml.registry import get_builder
from seedbank.infrastructure.storage import get_storage
from seedbank.services.model_registry_service import (
    ModelRegistryService,
    RegisterModelInput,
)

log = get_logger("seedbank.provision_smoke_model")

_BUILDER_KEY = "tiny-detector-smoke-v1"
_VERSION = "smoke-fixture"
_NAME = "Tiny Detector (smoke fixture)"
# Deterministic init so the serialized fixture bytes are reproducible run to run.
_SEED = 1234


def _serialize_random_weights() -> bytes:
    """Build the tiny detector and serialize its seed-fixed random state dict."""
    torch.manual_seed(_SEED)
    module = get_builder(_BUILDER_KEY)()
    buf = io.BytesIO()
    torch.save(module.state_dict(), buf)
    return buf.getvalue()


async def main() -> int:
    settings = get_settings()
    storage = get_storage()
    engine = create_async_engine(str(settings.postgres_dsn), future=True)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with sm() as session:
            models = ModelArtifactRepository(session)

            # Idempotent: a fresh stack has no production detector; a re-run
            # (or a real deployment that already promoted one) is a no-op.
            existing = await models.get_production(ModelKind.DETECTION, None)
            if existing is not None:
                log.info(
                    "provision_smoke_model.skip_existing_production",
                    model_id=str(existing.id),
                    name=existing.name,
                )
                return 0

            # ``created_by`` and the audit-log actor are FK → users.id, so use
            # the seeded admin as the operator rather than a synthetic UUID.
            stmt = select(User).where(User.role == UserRole.ADMIN.value).order_by(User.created_at)
            actor = (await session.execute(stmt)).scalars().first()
            if actor is None:
                log.error("provision_smoke_model.no_admin_user")
                return 2
            actor_id = actor.id

            bucket = settings.minio_bucket_models
            key = f"{_BUILDER_KEY}/{_VERSION}/weights.pth"
            artifact_uri = f"s3://{bucket}/{key}"

            # Upload first — register() and the promote transitions both verify
            # the object exists in MinIO before touching the hot path.
            data = _serialize_random_weights()
            await storage.ensure_bucket(bucket)
            await storage.put_object(bucket, key, data, "application/octet-stream")
            log.info("provision_smoke_model.uploaded", bytes=len(data), uri=artifact_uri)

            svc = ModelRegistryService(
                session=session, models=models, storage=storage, settings=settings
            )
            row = await svc.register(
                actor_id=actor_id,
                payload=RegisterModelInput(
                    name=_NAME,
                    version=_VERSION,
                    kind=ModelKind.DETECTION,
                    backend=ModelBackend.TORCH_LOCAL,
                    artifact_uri=artifact_uri,
                    seed_type_id=None,  # global detector — every scan routes to it
                    config={"builder_key": _BUILDER_KEY, "confidence_threshold": 0.5},
                    training_metadata={"fixture": True, "untrained": True},
                ),
            )
            # registered → staging → production (the enforced state machine).
            await svc.change_status(
                actor_id=actor_id, model_id=row.id, new_status=ModelStatus.STAGING
            )
            await svc.change_status(
                actor_id=actor_id, model_id=row.id, new_status=ModelStatus.PRODUCTION
            )
            log.info("provision_smoke_model.done", model_id=str(row.id), status="production")
    finally:
        await engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
