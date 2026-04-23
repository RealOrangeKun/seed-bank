"""Test-suite fixtures.

The integration tier uses `testcontainers` to spin up real Postgres / Redis /
MinIO / ClickHouse — never mocks. Unit tests don't need any of these.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING, Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

if TYPE_CHECKING:
    from httpx import AsyncClient


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


def _migrate_to_head(sync_dsn: str) -> None:
    """Apply alembic migrations using sync drivers.

    `alembic/env.py` calls `asyncio.run` in online mode, so this MUST NOT be
    invoked from a running event loop. Callers in async fixtures must wrap
    this in `asyncio.to_thread(...)`.
    """
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine

    sync_engine = create_engine(sync_dsn, future=True)
    with sync_engine.begin() as conn:
        conn.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS "citext"')
        conn.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
    sync_engine.dispose()

    repo_root = Path(__file__).resolve().parents[1]
    cfg = Config(str(repo_root / "alembic.ini"))
    cfg.set_main_option("script_location", str(repo_root / "alembic"))
    cfg.set_main_option("sqlalchemy.url", sync_dsn)
    command.upgrade(cfg, "head")


@pytest_asyncio.fixture
async def async_engine(postgres_container: Any) -> AsyncIterator[AsyncEngine]:
    """Async engine pointing at the testcontainer; baseline migration applied."""
    import asyncio

    sync_dsn = postgres_container.get_connection_url().replace(
        "postgresql+psycopg2://", "postgresql+psycopg://"
    )
    async_dsn = sync_dsn.replace("postgresql+psycopg://", "postgresql+asyncpg://")

    os.environ["POSTGRES_DSN"] = async_dsn
    from seedbank.core.config import get_settings

    get_settings.cache_clear()

    # Migrate in a worker thread so alembic's `asyncio.run(...)` can spin
    # up its own loop without colliding with our test loop.
    await asyncio.to_thread(_migrate_to_head, sync_dsn)

    engine = create_async_engine(async_dsn, future=True)
    try:
        yield engine
    finally:
        await engine.dispose()


async def _truncate_all_tables(engine: AsyncEngine) -> None:
    """TRUNCATE every user table in the public schema (preserves
    ``alembic_version`` so migrations are not re-run).

    Called from the function-scoped autouse fixtures in
    ``tests/integration/conftest.py`` and ``tests/e2e/conftest.py``. Lives
    here because both tiers need the same SQL and the same exclusion list.

    Why TRUNCATE instead of session-rollback: integration/e2e helpers call
    ``await session.commit()`` (the production code paths they exercise
    commit). A rollback at fixture teardown can't undo what another
    connection has already committed; TRUNCATE on the engine can.
    """
    from sqlalchemy import text

    async with engine.begin() as conn:
        rows = await conn.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = 'public' AND tablename != 'alembic_version'"
            )
        )
        tables = [r[0] for r in rows]
        if tables:
            quoted = ", ".join(f'"{t}"' for t in tables)
            await conn.execute(
                text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE")
            )


@pytest_asyncio.fixture
async def db_session(async_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    sm = async_sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession)
    async with sm() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def app_client(async_engine: AsyncEngine) -> AsyncIterator["AsyncClient"]:
    """FastAPI app wired to the testcontainer Postgres + a fake Redis.

    Lives at the top-level conftest so both ``tests/integration/`` (HTTP
    contract tests) and ``tests/e2e/`` (full flows) can depend on it.
    """
    from fakeredis import aioredis as fakeredis_aio
    from httpx import ASGITransport, AsyncClient

    fake_redis = fakeredis_aio.FakeRedis(decode_responses=True)

    sm: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=async_engine, expire_on_commit=False, class_=AsyncSession,
    )

    async def _override_db() -> AsyncIterator[AsyncSession]:
        async with sm() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    def _override_redis():
        return fake_redis

    from seedbank.api.deps import db_session as db_session_dep, redis_dep
    from seedbank.main import create_app

    app = create_app()
    app.dependency_overrides[db_session_dep] = _override_db
    app.dependency_overrides[redis_dep] = _override_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    await fake_redis.aclose()
