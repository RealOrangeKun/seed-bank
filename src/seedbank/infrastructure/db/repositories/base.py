"""Generic base repository.

Each aggregate gets its own subclass that adds use-case-specific queries on
top. Services depend on the *concrete* repository class (no Protocol indirection
unless multiple implementations exist) — keep it simple until a second backing
store appears.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.infrastructure.db.base import Base

T = TypeVar("T", bound=Base)


class Repository(Generic[T]):
    """Common CRUD primitives. Subclasses set ``model``."""

    model: type[T]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id: UUID) -> T | None:
        return await self.session.get(self.model, id)

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[T]:
        stmt = select(self.model).limit(limit).offset(offset)
        return list((await self.session.execute(stmt)).scalars().all())

    async def add(self, entity: T) -> T:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: T) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def find_by(self, **filters: Any) -> T | None:
        stmt = select(self.model).filter_by(**filters)
        return (await self.session.execute(stmt)).scalar_one_or_none()
