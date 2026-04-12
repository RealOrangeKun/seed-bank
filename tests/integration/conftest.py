"""Integration-test fixtures: app TestClient bound to the testcontainer DB.

Uses `fakeredis.aioredis.FakeRedis` to stand in for the real Redis client —
auth flows don't exercise atomic Redis ops beyond `set`/`get`/`delete`, so
fakeredis is faithful enough.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


@pytest_asyncio.fixture
async def app_client(async_engine: AsyncEngine) -> AsyncIterator[AsyncClient]:
    """Build a fresh FastAPI app wired to the testcontainer Postgres + a fake
    Redis."""
    from fakeredis import aioredis as fakeredis_aio

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

    # Build app *after* engine override so lifespan startup uses the test DB.
    from seedbank.api.deps import db_session, redis_dep
    from seedbank.main import create_app

    app = create_app()
    app.dependency_overrides[db_session] = _override_db
    app.dependency_overrides[redis_dep] = _override_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    await fake_redis.aclose()
