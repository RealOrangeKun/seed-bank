"""Per-process worker runtime: persistent event loop, engine, and redis.

Each Celery worker process owns:

1. ONE persistent ``asyncio`` event loop, set as the loop for this process.
2. ONE ``AsyncEngine`` (and its sessionmaker) created on that loop.
3. ONE ``redis.asyncio.Redis`` client created on that loop.

All three are constructed in :func:`init_worker_runtime` (called from
``worker_process_init`` *after* prefork) and torn down in
:func:`shutdown_worker_runtime` (called from ``worker_process_shutdown``).

Tasks run their async coroutine via :func:`run_async`, which executes on
this persistent loop instead of opening a fresh one with ``asyncio.run``.
That avoids two real bugs the prior per-task pattern had:

* ``asyncio.run`` closes the loop it creates; asyncpg / redis connections
  are bound to that loop, so a process-wide cached client crashed on the
  *second* task with ``RuntimeError('Event loop is closed')``.
* ``create_async_engine`` per task created (and disposed) a connection
  pool on every invocation — under load that's pool-creation churn x N.

Why not reuse ``seedbank.infrastructure.db.session.get_engine``? Because
that one is bound to the API process's loop via ``@lru_cache``. Workers
are a separate process tree (post-prefork) and need their own engine on
their own loop.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, TypeVar

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from seedbank.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Coroutine

    from seedbank.core.config import Settings

log = get_logger(__name__)

T = TypeVar("T")

_LOOP: asyncio.AbstractEventLoop | None = None
_ENGINE: AsyncEngine | None = None
_SESSIONMAKER: async_sessionmaker[AsyncSession] | None = None
_REDIS: Redis | None = None


def init_worker_runtime(settings: Settings) -> None:
    """Build the persistent loop + engine + redis. Called once per worker
    process from the ``worker_process_init`` signal.

    Idempotent: re-invoking is a no-op (defensive — Celery only fires the
    signal once per process under normal operation).
    """
    global _LOOP, _ENGINE, _SESSIONMAKER, _REDIS

    if _LOOP is not None:
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    engine = create_async_engine(str(settings.postgres_dsn), future=True)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    # ``Redis.from_url`` doesn't open a connection until first use, but
    # the asyncio primitives it allocates internally are bound to the
    # *current* loop. Build it on the persistent loop so subsequent
    # awaits don't trip "attached to a different loop".
    redis = loop.run_until_complete(_async_build_redis(settings))

    _LOOP = loop
    _ENGINE = engine
    _SESSIONMAKER = sm
    _REDIS = redis
    log.info("worker_runtime.initialised")


def shutdown_worker_runtime() -> None:
    """Dispose redis + engine, close the loop. Called once per worker
    process from the ``worker_process_shutdown`` signal.

    Order matters: close the higher-level clients first so any in-flight
    connections are returned to the pool before we tear the pool down.
    """
    global _LOOP, _ENGINE, _SESSIONMAKER, _REDIS

    if _LOOP is None:
        return

    try:
        if _REDIS is not None:
            _LOOP.run_until_complete(_REDIS.aclose())
        if _ENGINE is not None:
            _LOOP.run_until_complete(_ENGINE.dispose())
    finally:
        _LOOP.close()
        _LOOP = None
        _ENGINE = None
        _SESSIONMAKER = None
        _REDIS = None
        log.info("worker_runtime.shutdown")


def run_async(coro: Coroutine[object, object, T]) -> T:
    """Schedule a coroutine on the worker process's persistent loop.

    Replaces ``asyncio.run(coro)`` in worker task entry points so the
    same loop (and its engine/redis bindings) is reused across tasks.
    """
    if _LOOP is None:
        # Fallback for environments where the worker_process_init signal
        # hasn't fired (e.g. ``CELERY_TASK_ALWAYS_EAGER=1`` in tests). In
        # that case fresh-loop-per-call is the right behaviour — tests
        # don't share state across cases.
        return asyncio.run(coro)
    return _LOOP.run_until_complete(coro)


def get_worker_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the process-scoped sessionmaker.

    When the worker runtime hasn't been initialised (e.g. tests running
    with ``celery_task_always_eager=True`` — the prefork signals don't
    fire), fall back to the API-side sessionmaker so the test loop owns
    the engine. In a real worker this fallback never runs.
    """
    if _SESSIONMAKER is None:
        from seedbank.infrastructure.db.session import get_sessionmaker

        return get_sessionmaker()
    return _SESSIONMAKER


def get_worker_redis() -> Redis:
    """Return the process-scoped redis client.

    Same eager-mode fallback as :func:`get_worker_sessionmaker`.
    """
    if _REDIS is None:
        from seedbank.infrastructure.cache.redis_client import get_redis

        return get_redis()
    return _REDIS


async def _async_build_redis(settings: Settings) -> Redis:
    """Build the Redis client *inside* the loop.

    ``Redis.from_url`` itself is sync, but calling it inside a coroutine
    guarantees that the asyncio primitives it allocates (locks, futures)
    are tied to the loop we want.
    """
    client: Redis = Redis.from_url(
        str(settings.redis_dsn),
        encoding="utf-8",
        decode_responses=True,
        health_check_interval=30,
    )
    return client


__all__ = [
    "get_worker_redis",
    "get_worker_sessionmaker",
    "init_worker_runtime",
    "run_async",
    "shutdown_worker_runtime",
]
