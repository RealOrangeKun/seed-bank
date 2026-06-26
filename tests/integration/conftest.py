"""Integration-tier fixtures.

The ``app_client`` fixture lives in the top-level ``tests/conftest.py`` so
e2e tests inherit it without re-import. Tier-specific hygiene (slowapi
limiter reset, DB truncation) lives here so the unit tier — which has no
Redis or Postgres access — is not forced to wait on connection retries.
"""

from __future__ import annotations

import os

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
