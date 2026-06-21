"""API-key repository."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update

from seedbank.infrastructure.db.models import ApiKey

from .base import Repository


class ApiKeyRepository(Repository[ApiKey]):
    model = ApiKey

    async def get_active_by_hash(self, key_hash: str) -> ApiKey | None:
        now = datetime.now(tz=UTC)
        stmt = select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.revoked_at.is_(None),
        )
        key = (await self.session.execute(stmt)).scalar_one_or_none()
        if key is None:
            return None
        if key.expires_at is not None and key.expires_at <= now:
            return None
        return key

    async def list_for_user(
        self, user_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[ApiKey]:
        stmt = (
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_for_user(self, user_id: UUID) -> int:
        stmt = select(func.count()).select_from(ApiKey).where(ApiKey.user_id == user_id)
        return int((await self.session.execute(stmt)).scalar_one())

    async def revoke(self, key_id: UUID, user_id: UUID) -> bool:
        """Revoke a key the user owns. Returns True if a row was updated."""
        stmt = (
            update(ApiKey)
            .where(
                ApiKey.id == key_id,
                ApiKey.user_id == user_id,
                ApiKey.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(tz=UTC))
        )
        result = await self.session.execute(stmt)
        return (result.rowcount or 0) > 0  # type: ignore[attr-defined]

    async def touch_last_used(self, key_id: UUID) -> None:
        stmt = update(ApiKey).where(ApiKey.id == key_id).values(last_used_at=datetime.now(tz=UTC))
        await self.session.execute(stmt)
