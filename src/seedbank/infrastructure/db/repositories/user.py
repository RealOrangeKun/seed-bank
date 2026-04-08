"""User repository — narrow methods the auth & user services need."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update

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
