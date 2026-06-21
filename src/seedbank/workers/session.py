"""Worker-scoped async session helper.

Yields an ``AsyncSession`` from the process-scoped sessionmaker built in
:mod:`seedbank.workers.runtime`. The engine itself is created exactly
once per worker process (in the ``worker_process_init`` signal) and
disposed on shutdown — no per-task pool churn.

Why not reuse the API's ``@lru_cache``-d engine in
``seedbank.infrastructure.db.session``? Because that one is bound to the
API's event loop. Workers run their own persistent loop and need their
own engine on it.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from seedbank.workers.runtime import get_worker_sessionmaker

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def worker_session_scope() -> AsyncIterator[AsyncSession]:
    """Yield a fresh ``AsyncSession`` from the process-scoped pool."""
    sm = get_worker_sessionmaker()
    async with sm() as session:
        yield session


__all__ = ["worker_session_scope"]
