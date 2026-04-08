"""Async SQLAlchemy engine + session factory.

Single source of truth for the OLTP database connection. Routers must obtain a
session via the FastAPI dependency `get_db()`; service-level code receives an
`AsyncSession` injected from the same factory and never instantiates one
directly.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from seedbank.core.config import Settings, get_settings


def _build_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        str(settings.postgres_dsn),
        echo=settings.postgres_echo,
        pool_size=settings.postgres_pool_size,
        max_overflow=settings.postgres_max_overflow,
        pool_timeout=settings.postgres_pool_timeout,
        pool_pre_ping=True,
        future=True,
    )


@lru_cache(maxsize=1)
def get_engine() -> AsyncEngine:
    """Return a process-wide cached `AsyncEngine`.

    Tests override by clearing the cache after swapping `Settings`.
    """
    return _build_engine(get_settings())


@lru_cache(maxsize=1)
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return a process-wide cached `async_sessionmaker`."""
    return async_sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
        class_=AsyncSession,
    )


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a managed `AsyncSession`.

    Wraps the request in an outer transaction-on-commit pattern: the caller may
    `await session.commit()` or `await session.rollback()` itself. On unhandled
    exception we rollback; the session is always closed.
    """
    sessionmaker = get_sessionmaker()
    session: AsyncSession = sessionmaker()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def dispose_engine() -> None:
    """Close the engine pool. Call on app shutdown."""
    engine = get_engine()
    await engine.dispose()
