"""FastAPI dependencies — the only place routers reach into infrastructure.

Routers depend on these getters; they never instantiate engines, clients, or
services themselves. The `current_user` / `require_role` dependencies live
here too so RBAC is one decoration away on any route.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.core.config import Settings, get_settings
from seedbank.infrastructure.analytics import ClickHouseClient, get_clickhouse
from seedbank.infrastructure.cache import get_redis
from seedbank.infrastructure.db.session import get_db as _get_db
from seedbank.infrastructure.storage import MinioStorage, get_storage


async def db_session() -> AsyncIterator[AsyncSession]:
    """Yield an `AsyncSession` for the lifetime of one request."""
    async for s in _get_db():
        yield s


def settings_dep() -> Settings:
    return get_settings()


def redis_dep() -> Redis:
    return get_redis()


def storage_dep() -> MinioStorage:
    return get_storage()


async def clickhouse_dep() -> ClickHouseClient:
    return await get_clickhouse()


# Type aliases for terser router signatures.
DbSession = Annotated[AsyncSession, Depends(db_session)]
SettingsDep = Annotated[Settings, Depends(settings_dep)]
RedisDep = Annotated[Redis, Depends(redis_dep)]
StorageDep = Annotated[MinioStorage, Depends(storage_dep)]
ClickHouseDep = Annotated[ClickHouseClient, Depends(clickhouse_dep)]


# `current_user` / `require_role` are added in Phase 4 (auth) — this stub
# avoids forward-import churn when routers start declaring `User` deps now.
