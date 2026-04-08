"""ModelArtifact repository — the registry that the ML platform reads from."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from seedbank.infrastructure.db.enums import ModelKind, ModelStatus
from seedbank.infrastructure.db.models import ModelArtifact

from .base import Repository


class ModelArtifactRepository(Repository[ModelArtifact]):
    model = ModelArtifact

    async def get_production(
        self, kind: ModelKind, seed_type_id: UUID | None
    ) -> ModelArtifact | None:
        """The single production model for `(kind, seed_type_id)`. Returns None
        when nothing is promoted yet. NULL `seed_type_id` matches NULL
        (SQL's three-valued logic — we use `IS NULL` not `=`)."""
        seed_filter = (
            ModelArtifact.seed_type_id.is_(None)
            if seed_type_id is None
            else ModelArtifact.seed_type_id == seed_type_id
        )
        stmt = select(ModelArtifact).where(
            ModelArtifact.kind == kind.value,
            seed_filter,
            ModelArtifact.status == ModelStatus.PRODUCTION.value,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_active(self) -> list[ModelArtifact]:
        """All non-archived models — the registry as the platform sees it."""
        stmt = (
            select(ModelArtifact)
            .where(ModelArtifact.status != ModelStatus.ARCHIVED.value)
            .order_by(ModelArtifact.kind, ModelArtifact.name, ModelArtifact.version)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_by_status(self, status: ModelStatus) -> list[ModelArtifact]:
        stmt = select(ModelArtifact).where(ModelArtifact.status == status.value)
        return list((await self.session.execute(stmt)).scalars().all())

    async def find_by_name_version(self, name: str, version: str) -> ModelArtifact | None:
        stmt = select(ModelArtifact).where(
            ModelArtifact.name == name, ModelArtifact.version == version
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
