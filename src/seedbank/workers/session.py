"""Worker-scoped async session helper.

Each Celery task opens its own engine + sessionmaker and disposes the
engine when the task ends. This is **required**: the API process keeps a
process-wide engine via ``@lru_cache`` in
:mod:`seedbank.infrastructure.db.session`, but reusing it from inside
``asyncio.run(...)`` in a worker would tie its asyncpg connections to a
loop that closes when the task returns — the next task would crash.

Pattern is verbatim from ``scripts/register_model.py:116-153``.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from seedbank.core.config import get_settings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@asynccontextmanager
async def worker_session_scope() -> AsyncIterator[AsyncSession]:
    """Yield a fresh ``AsyncSession`` backed by a per-call engine.

    The engine is disposed in ``finally`` so connection pools never leak
    across Celery task invocations.
    """
    settings = get_settings()
    engine = create_async_engine(str(settings.postgres_dsn), future=True)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with sm() as session:
            yield session
    finally:
        await engine.dispose()


__all__ = ["worker_session_scope"]
