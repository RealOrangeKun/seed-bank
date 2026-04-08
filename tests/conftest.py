"""Test-suite fixtures.

The integration tier uses `testcontainers` to spin up real Postgres / Redis /
MinIO / ClickHouse — never mocks. Unit tests don't need any of these.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[Any]:
    """Session-scoped Postgres container. Skipped automatically when the
    integration extras aren't installed."""
    pytest.importorskip("testcontainers.postgres")
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest_asyncio.fixture
async def async_engine(postgres_container: Any) -> AsyncIterator[AsyncEngine]:
    """Async engine pointing at the testcontainer; baseline migration applied."""
    from sqlalchemy import create_engine

    sync_dsn = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+psycopg://"
    )
    async_dsn = sync_dsn.replace("postgresql+psycopg://", "postgresql+asyncpg://")

    sync_engine = create_engine(sync_dsn, future=True)
    with sync_engine.begin() as conn:
        conn.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS "citext"')
        conn.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
    sync_engine.dispose()

    os.environ["POSTGRES_DSN"] = async_dsn
    from seedbank.core.config import get_settings

    get_settings.cache_clear()

    # Apply the baseline migration up to head.
    from alembic import command
    from alembic.config import Config
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(repo_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(repo_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", sync_dsn)
    command.upgrade(cfg, "head")

    engine = create_async_engine(async_dsn, future=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(async_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    sm = async_sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession)
    async with sm() as session:
        yield session
        await session.rollback()
