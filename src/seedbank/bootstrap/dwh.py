"""ClickHouse / DWH bootstrap.

Three operations used by both ``init_clickhouse`` and ``seed_dev`` CLIs:

1. :func:`ensure_clickhouse_database` — create the configured database
   if missing. Uses the sync ``clickhouse_connect`` client against the
   ``default`` system DB because the async client expects the target DB
   to exist at handshake time.
2. :func:`apply_dwh_schema` — run the project DDL (``CREATE TABLE IF
   NOT EXISTS`` everywhere) so it's safe to call on every container start.
3. :func:`mirror_seed_types_to_dwh` — copy the OLTP catalog into
   ``dim_seed_type`` so the first ``fact_*`` joins resolve immediately.

Each function takes its dependencies as arguments — no ``get_settings()``
inside, no engine creation. CLIs build collaborators and pass them in.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import clickhouse_connect
from sqlalchemy import select

from seedbank.core.logging import get_logger
from seedbank.infrastructure.analytics import (
    AnalyticsRepository,
    DimSeedTypeRow,
    apply_schema,
)
from seedbank.infrastructure.db.models import SeedType

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from seedbank.core.config import Settings
    from seedbank.infrastructure.analytics import ClickHouseClient

log = get_logger(__name__)


def ensure_clickhouse_database(settings: Settings) -> None:
    """Create the configured ClickHouse database if it doesn't exist.

    Uses the sync client against ``default`` so handshake succeeds even
    on a fresh ClickHouse instance.
    """
    sync_client = clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password.get_secret_value(),
        database="default",
        connect_timeout=10,
    )
    try:
        sync_client.command(f"CREATE DATABASE IF NOT EXISTS {settings.clickhouse_database}")
        log.info("dwh.database_ensured", database=settings.clickhouse_database)
    finally:
        sync_client.close()


async def apply_dwh_schema(client: ClickHouseClient) -> None:
    """Apply the project's ClickHouse DDL. Idempotent."""
    await apply_schema(client)


async def mirror_seed_types_to_dwh(session: AsyncSession, repo: AnalyticsRepository) -> int:
    """Copy ``seed_types`` rows from OLTP into ``dim_seed_type``.

    Returns the number of rows mirrored. ``upsert_seed_types`` is
    idempotent so re-running is safe.
    """
    rows = list((await session.execute(select(SeedType))).scalars().all())
    if not rows:
        log.info("dwh.seed_types_skipped", reason="empty_catalog")
        return 0
    await repo.upsert_seed_types(
        DimSeedTypeRow(
            seed_type_id=st.id,
            code=st.code,
            display_name=st.display_name,
            default_confidence_threshold=st.default_confidence_threshold,
            created_at=st.created_at,
            updated_at=st.updated_at,
        )
        for st in rows
    )
    log.info("dwh.seed_types_synced", n=len(rows))
    return len(rows)


async def bootstrap_clickhouse(settings: Settings) -> int:
    """End-to-end ClickHouse bootstrap: ensure DB + apply schema + mirror
    the seed-type catalog from OLTP. Returns the number of seed types
    mirrored.

    Owns its own short-lived OLTP engine and ClickHouse client so the
    caller doesn't have to thread either through. CLIs that want finer
    control (e.g. share an OLTP session with other bootstrap calls) can
    invoke the three functions directly instead.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from seedbank.infrastructure.analytics import ClickHouseClient

    ensure_clickhouse_database(settings)
    client = await ClickHouseClient.from_settings(settings)
    try:
        await apply_dwh_schema(client)
        repo = AnalyticsRepository(client)
        engine = create_async_engine(str(settings.postgres_dsn), future=True)
        sm = async_sessionmaker(bind=engine, expire_on_commit=False)
        try:
            async with sm() as session:
                return await mirror_seed_types_to_dwh(session, repo)
        finally:
            await engine.dispose()
    finally:
        await client.close()
