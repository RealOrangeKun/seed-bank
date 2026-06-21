"""User repository — narrow methods the auth & user services need."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, update

from seedbank.infrastructure.db.models import User

from .base import Repository


class UserRepository(Repository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email, User.deleted_at.is_(None))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_by_id_active(self, user_id: UUID) -> User | None:
        user = await self.session.get(User, user_id)
        if user is None or user.deleted_at is not None or not user.is_active:
            return None
        return user

    async def touch_last_login(self, user_id: UUID) -> None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.now(tz=timezone.utc))
        )
        await self.session.execute(stmt)

    async def mark_verified(self, user_id: UUID) -> int:
        stmt = (
            update(User)
            .where(User.id == user_id, User.is_verified.is_(False))
            .values(is_verified=True)
        )
        return (await self.session.execute(stmt)).rowcount or 0

    async def update_password(self, user_id: UUID, hashed_password: str) -> None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(hashed_password=hashed_password)
        )
        await self.session.execute(stmt)

    async def set_role(self, user_id: UUID, role: str) -> int:
        stmt = update(User).where(User.id == user_id).values(role=role)
        return (await self.session.execute(stmt)).rowcount or 0

    async def list_active(
        self, *, limit: int = 50, offset: int = 0
    ) -> list[User]:
        stmt = (
            select(User)
            .where(User.deleted_at.is_(None))
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_active(self) -> int:
        stmt = select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        return int((await self.session.execute(stmt)).scalar_one())

    async def exists_with_role(self, role: str) -> bool:
        """Truthy iff at least one non-deleted user holds ``role``.

        Used by the bootstrap-admin path to enforce the "exactly one
        first admin" rule without loading any rows.
        """
        stmt = (
            select(User.id)
            .where(User.role == role, User.deleted_at.is_(None))
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none() is not None
