"""Async Redis client.

One pool per process. Used as cache, rate-limit counter, and Celery broker
(via celery's own connection — different DB).
"""

from __future__ import annotations

from functools import lru_cache

from redis.asyncio import Redis

from seedbank.core.config import Settings, get_settings


def _build_redis(settings: Settings) -> Redis:
    client: Redis = Redis.from_url(
        str(settings.redis_dsn),
        encoding="utf-8",
        decode_responses=True,
        health_check_interval=30,
    )
    return client


@lru_cache(maxsize=1)
def get_redis() -> Redis:
    return _build_redis(get_settings())


async def close_redis() -> None:
    redis = get_redis()
    await redis.aclose()
