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

# The slowapi limiter is built at import time from Settings; its default storage
# is the real Redis DSN (redis:6379), which is unreachable in the test env.
# Force in-process storage BEFORE any seedbank module is imported so no
# rate-limited route dials a live Redis. `memory://` still rate-limits, so 429
# behaviour stays testable.
os.environ.setdefault("RATE_LIMIT_STORAGE_URI", "memory://")

if TYPE_CHECKING:
    from httpx import AsyncClient
    from redis.asyncio import Redis


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


@pytest.fixture(scope="session")
def clickhouse_container() -> Iterator[Any]:
    """Session-scoped ClickHouse container for the DWH integration tier.

    Pinned to 24.10-alpine to match what compose runs in dev/prod —
    keeps the test surface honest. Skipped automatically when the
    integration extras aren't installed (so the unit + e2e tiers, which
    don't import this fixture, never pay the spin-up cost).
    """
    pytest.importorskip("testcontainers.clickhouse")
    from testcontainers.clickhouse import ClickHouseContainer

    # Username/password/dbname default to "test" inside the container; we
    # override CLICKHOUSE_DB explicitly so the dim/fact DDL has somewhere
    # to land on first apply.
    with ClickHouseContainer(
        "clickhouse/clickhouse-server:24.10-alpine",
        username="test",
        password="test",
        dbname="seedbank_test",
    ) as ch:
        yield ch


_DWH_TABLES = (
    "fact_inference",
    "fact_detection",
    "fact_experiment_result",
    "fact_scan_batch",
    "dim_user",
    "dim_seed_type",
    "dim_model",
)


@pytest_asyncio.fixture
async def clickhouse_client(clickhouse_container: Any) -> AsyncIterator[Any]:
    """Async ClickHouse client wired to the testcontainer.

    Spins the container's HTTP port (8123) into ``Settings``, clears the
    settings cache AND the process-wide ``get_clickhouse`` client (so the
    app's ``ClickHouseDep`` and worker tasks rebuild against the container
    rather than a default ``clickhouse:8123`` instance cached by an earlier
    test), applies the star-schema DDL, and yields a :class:`ClickHouseClient`.

    Lives at the top level so BOTH tiers can wire ClickHouse: integration
    (dual-write) and e2e (the ``/models/{id}/performance`` read path).

    **Function-scoped on purpose.** ``clickhouse-connect``'s async client binds
    its socket to the event loop it was created on; pytest-asyncio runs each
    test (and the function-scoped ``db_session``/``async_engine``) on its own
    loop, so a session-scoped client would be reused across loops and raise
    ``KeyError: <fileobj> is not registered`` from the selector. Rebuilding per
    test keeps it on the test's loop. DDL is idempotent (CREATE IF NOT EXISTS);
    the container stays session-scoped; per-test isolation is via
    ``_truncate_clickhouse``.
    """
    from seedbank.core.config import get_settings
    from seedbank.infrastructure.analytics import ClickHouseClient, apply_schema
    from seedbank.infrastructure.analytics.clickhouse_client import close_clickhouse

    host = clickhouse_container.get_container_host_ip()
    http_port = clickhouse_container.get_exposed_port(8123)

    os.environ["CLICKHOUSE_HOST"] = host
    os.environ["CLICKHOUSE_PORT"] = str(http_port)
    os.environ["CLICKHOUSE_USER"] = "test"
    os.environ["CLICKHOUSE_PASSWORD"] = "test"
    os.environ["CLICKHOUSE_DATABASE"] = "seedbank_test"
    get_settings.cache_clear()
    await close_clickhouse()

    client = await ClickHouseClient.from_settings(get_settings())
    try:
        await apply_schema(client)
        yield client
    finally:
        await client.close()
        await close_clickhouse()


@pytest_asyncio.fixture(autouse=False)
async def _truncate_clickhouse(clickhouse_client: Any) -> None:
    """TRUNCATE every dim/fact table before each test that asks for
    ``clickhouse_client``. Not autouse — only DWH-touching tests pay the
    round-trip (testcontainers are session-scoped; isolation is per-test).
    """
    for table in _DWH_TABLES:
        await clickhouse_client.execute(f"TRUNCATE TABLE {table}")


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
            await conn.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))


@pytest_asyncio.fixture
async def db_session(async_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    sm = async_sessionmaker(bind=async_engine, expire_on_commit=False, class_=AsyncSession)
    async with sm() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def app_client(async_engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    """FastAPI app wired to the testcontainer Postgres + a fake Redis.

    Lives at the top-level conftest so both ``tests/integration/`` (HTTP
    contract tests) and ``tests/e2e/`` (full flows) can depend on it.
    """
    from fakeredis import aioredis as fakeredis_aio
    from httpx import ASGITransport, AsyncClient

    fake_redis = fakeredis_aio.FakeRedis(decode_responses=True)

    sm: async_sessionmaker[AsyncSession] = async_sessionmaker(
        bind=async_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async def _override_db() -> AsyncIterator[AsyncSession]:
        async with sm() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    def _override_redis() -> Redis:
        return fake_redis

    from seedbank.api.deps import db_session as db_session_dep
    from seedbank.api.deps import redis_dep
    from seedbank.main import create_app

    app = create_app()
    app.dependency_overrides[db_session_dep] = _override_db
    app.dependency_overrides[redis_dep] = _override_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    await fake_redis.aclose()
