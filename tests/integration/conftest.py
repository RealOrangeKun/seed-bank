"""Integration-tier fixtures.

The ``app_client`` fixture lives in the top-level ``tests/conftest.py`` so
e2e tests inherit it without re-import. Tier-specific hygiene (slowapi
limiter reset, DB truncation) lives here so the unit tier — which has no
Redis or Postgres access — is not forced to wait on connection retries.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.conftest import _truncate_all_tables

# Phase 8 — ``tests/e2e/conftest.py`` sets DWH_ENABLED=false at module-load
# time so eager tests don't try to dial ClickHouse. The integration tier
# explicitly flips it back: dual-write is exactly what's under test here.
os.environ["DWH_ENABLED"] = "true"


@pytest_asyncio.fixture(autouse=True)
async def _truncate_db(async_engine: AsyncEngine) -> None:
    """TRUNCATE every user table before every integration test.

    Per the testing skill: "Containers are session-scoped, not per-test.
    State is reset by truncating tables in a function-scoped fixture."
    """
    await _truncate_all_tables(async_engine)


@pytest_asyncio.fixture(autouse=True)
async def _reset_rate_limiter() -> None:
    """Clear the slowapi Limiter singleton's storage before every test.

    The Limiter is constructed at module import time and points at the
    process-wide Redis configured by ``Settings.redis_dsn``. Without a
    reset, the auth/login bucket (10/min) accumulates counts across tests
    and produces spurious 429s on tests that legitimately call ``/login``.

    Narrow excepts: ``StorageError`` covers "limits backend rejected the
    op", ``RedisConnectionError`` covers "Redis container unreachable" —
    both are tolerable when the suite runs without infra. Any other
    exception is a real bug and surfaces.
    """
    import contextlib

    from limits.errors import StorageError
    from redis.exceptions import ConnectionError as RedisConnectionError

    from seedbank.api.rate_limit import limiter

    with contextlib.suppress(StorageError, RedisConnectionError):
        limiter.reset()


# ── ClickHouse fixtures (Phase 8 dual-write) ──────────────────────────────


_DWH_TABLES = (
    "fact_inference",
    "fact_detection",
    "fact_experiment_result",
    "fact_scan_batch",
    "dim_user",
    "dim_seed_type",
    "dim_model",
)


@pytest_asyncio.fixture(scope="session")
async def clickhouse_client(clickhouse_container: Any) -> AsyncIterator[Any]:
    """Async ClickHouse client wired to the testcontainer.

    Spins the container's HTTP port (8123) into ``Settings``, clears the
    settings cache so worker tasks pick up the testcontainer, applies the
    star-schema DDL once, and yields a :class:`ClickHouseClient`.

    Session-scoped — DDL is idempotent, and per-test isolation is via
    ``_truncate_clickhouse`` below.
    """
    from seedbank.core.config import get_settings
    from seedbank.infrastructure.analytics import (
        ClickHouseClient,
        apply_schema,
    )

    host = clickhouse_container.get_container_host_ip()
    http_port = clickhouse_container.get_exposed_port(8123)

    os.environ["CLICKHOUSE_HOST"] = host
    os.environ["CLICKHOUSE_PORT"] = str(http_port)
    os.environ["CLICKHOUSE_USER"] = "test"
    os.environ["CLICKHOUSE_PASSWORD"] = "test"
    os.environ["CLICKHOUSE_DATABASE"] = "seedbank_test"
    get_settings.cache_clear()

    client = await ClickHouseClient.from_settings(get_settings())
    try:
        await apply_schema(client)
        yield client
    finally:
        await client.close()


@pytest_asyncio.fixture(autouse=False)
async def _truncate_clickhouse(clickhouse_client: Any) -> None:
    """TRUNCATE every dim/fact table before each integration test that
    asks for ``clickhouse_client``.

    Not autouse — only DWH-touching tests pay the round-trip. Mirrors
    the rationale for ``_truncate_db``: testcontainers are session-scoped,
    isolation comes from per-test truncation.
    """
    for table in _DWH_TABLES:
        await clickhouse_client.execute(f"TRUNCATE TABLE {table}")
