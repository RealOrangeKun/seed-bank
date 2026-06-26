"""Model registry service — CRUD + status transitions on ``model_artifacts``.

Status state machine (enforced here, not in the schema):

    registered → staging → production → archived
                       └→ archived
                       ↑
            (any state → archived is allowed)

Promoting to ``production`` automatically archives the previous production
row for the same ``(kind, seed_type_id)`` in the same transaction; the DB
partial-unique index is the safety net if two concurrent promotes race.

Every transition writes an ``audit_log`` row keyed by ``model_id``. The
service never raises ``HTTPException`` — domain errors only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.core.config import Settings, get_settings
from seedbank.core.exceptions import (
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    ValidationError,
)
from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.enums import ModelBackend, ModelKind, ModelStatus
from seedbank.infrastructure.db.models import AuditLog, ModelArtifact
from seedbank.infrastructure.db.repositories import ModelArtifactRepository
from seedbank.infrastructure.storage import MinioStorage

log = get_logger(__name__)


# Allowed forward transitions. ``archived`` is a terminal sink reachable
# from anywhere except itself.
_TRANSITIONS: dict[ModelStatus, frozenset[ModelStatus]] = {
    ModelStatus.REGISTERED: frozenset({ModelStatus.STAGING, ModelStatus.ARCHIVED}),
    ModelStatus.STAGING: frozenset({ModelStatus.PRODUCTION, ModelStatus.ARCHIVED}),
    ModelStatus.PRODUCTION: frozenset({ModelStatus.ARCHIVED}),
    ModelStatus.ARCHIVED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class RegisterModelInput:
    name: str
    version: str
    kind: ModelKind
    backend: ModelBackend
    artifact_uri: str
    seed_type_id: UUID | None = None
    config: dict[str, Any] | None = None
    training_metadata: dict[str, Any] | None = None
    mlflow_run_id: str | None = None


class ModelRegistryService:
    """Use-case orchestrator on top of ``ModelArtifactRepository``."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        models: ModelArtifactRepository,
        storage: MinioStorage,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.models = models
        self.storage = storage
        self.settings = settings or get_settings()

    # ── Read ─────────────────────────────────────────────────────────────────

    async def get(self, model_id: UUID) -> ModelArtifact:
        row = await self.models.get(model_id)
        if row is None:
            raise NotFoundError(f"Model {model_id} not found.")
        return row

    async def list(
        self,
        *,
        kind: ModelKind | None = None,
        status: ModelStatus | None = None,
        seed_type_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[ModelArtifact], int]:
        """Filtered, paginated registry listing. Returns ``(rows, total)`` so
        the router can build a ``Page[T]`` envelope without a second round-trip
        from a count helper."""
        filters = []
        if kind is not None:
            filters.append(ModelArtifact.kind == kind.value)
        if status is not None:
            filters.append(ModelArtifact.status == status.value)
        if seed_type_id is not None:
            filters.append(ModelArtifact.seed_type_id == seed_type_id)

        stmt = select(ModelArtifact)
        for f in filters:
            stmt = stmt.where(f)
        stmt = (
            stmt.order_by(ModelArtifact.kind, ModelArtifact.name, ModelArtifact.version)
            .limit(limit)
            .offset(offset)
        )
        rows = list((await self.session.execute(stmt)).scalars().all())

        count_stmt = select(func.count()).select_from(ModelArtifact)
        for f in filters:
            count_stmt = count_stmt.where(f)
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return rows, total

    # ── Write ────────────────────────────────────────────────────────────────

    async def register(
        self,
        *,
        actor_id: UUID,
        payload: RegisterModelInput,
        ip: str | None = None,
    ) -> ModelArtifact:
        """Create a fresh ``model_artifacts`` row in ``registered`` state.

        The ``artifact_uri`` is verified to exist in the models bucket
        (we don't pre-fetch the bytes — an existence check is enough to
        catch typo'd URIs).
        """
        # Reject duplicate (name, version) early with a domain error rather
        # than letting the unique constraint surface as a generic 500.
        existing = await self.models.find_by_name_version(payload.name, payload.version)
        if existing is not None:
            raise ConflictError(f"Model {payload.name}:{payload.version} already registered.")

        await self._verify_artifact_exists(payload.artifact_uri)

        row = ModelArtifact(
            name=payload.name,
            version=payload.version,
            kind=payload.kind.value,
            backend=payload.backend.value,
            seed_type_id=payload.seed_type_id,
            artifact_uri=payload.artifact_uri,
            config=payload.config,
            training_metadata=payload.training_metadata,
            mlflow_run_id=payload.mlflow_run_id,
            status=ModelStatus.REGISTERED.value,
            created_by=actor_id,
        )
        await self.models.add(row)

        self.session.add(
            AuditLog(
                actor_id=actor_id,
                action="model.register",
                target_type="model_artifact",
                target_id=str(row.id),
                audit_metadata={
                    "name": payload.name,
                    "version": payload.version,
                    "kind": payload.kind.value,
                    "backend": payload.backend.value,
                },
                ip=ip,
            )
        )
        await self.session.commit()
        log.info(
            "model.registered",
            model_id=str(row.id),
            name=row.name,
            version=row.version,
        )
        return row

    async def change_status(
        self,
        *,
        actor_id: UUID,
        model_id: UUID,
        new_status: ModelStatus,
        ip: str | None = None,
    ) -> ModelArtifact:
        """Move ``model_id`` to ``new_status`` if the transition is allowed."""
        row = await self.models.get(model_id)
        if row is None:
            raise NotFoundError(f"Model {model_id} not found.")

        current = ModelStatus(row.status)
        if current is new_status:
            return row  # idempotent no-op
        allowed = _TRANSITIONS[current]
        if new_status not in allowed:
            raise ConflictError(f"Illegal transition {current.value} → {new_status.value}.")

        # Verify the artifact still exists in MinIO before promoting it onto
        # the staging/production hot path. Skipped for archive transitions.
        if new_status in {ModelStatus.STAGING, ModelStatus.PRODUCTION}:
            await self._verify_artifact_exists(row.artifact_uri)

        # Promotion to production demotes the incumbent in the same txn so
        # the partial-unique index never sees two productions for the segment.
        if new_status is ModelStatus.PRODUCTION:
            incumbent = await self.models.get_production(ModelKind(row.kind), row.seed_type_id)
            if incumbent is not None and incumbent.id != row.id:
                incumbent.status = ModelStatus.ARCHIVED.value
                self.session.add(
                    AuditLog(
                        actor_id=actor_id,
                        action="model.status_change",
                        target_type="model_artifact",
                        target_id=str(incumbent.id),
                        audit_metadata={
                            "from": ModelStatus.PRODUCTION.value,
                            "to": ModelStatus.ARCHIVED.value,
                            "reason": f"superseded by {row.id}",
                        },
                        ip=ip,
                    )
                )

        row.status = new_status.value
        self.session.add(
            AuditLog(
                actor_id=actor_id,
                action="model.status_change",
                target_type="model_artifact",
                target_id=str(row.id),
                audit_metadata={"from": current.value, "to": new_status.value},
                ip=ip,
            )
        )
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

        # ``updated_at`` is server-managed via ``onupdate=func.now()`` —
        # SQLAlchemy marks the column as needing re-fetch after UPDATE, and
        # without an explicit refresh the next access (e.g. Pydantic
        # serialization at the router boundary) triggers a lazy load
        # outside the await context, raising ``MissingGreenlet``. Refresh
        # synchronously here so callers get a fully-loaded row back.
        await self.session.refresh(row)

        log.info(
            "model.status_changed",
            model_id=str(row.id),
            from_=current.value,
            to=new_status.value,
        )
        return row

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _bucket_and_key(uri: str, default_bucket: str) -> tuple[str, str]:
        if uri.startswith("s3://"):
            rest = uri.removeprefix("s3://")
            bucket, _, key = rest.partition("/")
            return bucket or default_bucket, key
        if uri.startswith("roboflow://"):
            # External backend — nothing to verify in MinIO.
            return "", ""
        return default_bucket, uri

    async def _verify_artifact_exists(self, artifact_uri: str) -> None:
        bucket, key = self._bucket_and_key(artifact_uri, self.settings.minio_bucket_models)
        if not bucket or not key:
            return  # External (e.g. Roboflow) — skip existence check.
        try:
            exists = await self.storage.object_exists(bucket, key)
        except ExternalServiceError:
            raise
        if not exists:
            raise ValidationError(f"Artifact {bucket}/{key} not found in object storage.")


__all__ = ["ModelRegistryService", "RegisterModelInput"]
