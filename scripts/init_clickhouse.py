"""Bootstrap the ClickHouse star schema.

Run-anywhere idempotent script that ensures:

1. The configured database exists.
2. Every table from ``schema.sql`` exists (``CREATE TABLE IF NOT EXISTS``).
3. The ``dim_seed_type`` table is seeded from the OLTP catalog so the
   first ``fact_*`` joins resolve immediately. (Models / users sync on
   write — but seed types are bootstrapped in Postgres at deploy time
   and never go through a public API, so we sync them here.)

Usage::

    python scripts/init_clickhouse.py

The script is invoked by ``make seed`` and (in compose) is safe to call
on every container start. It exits non-zero only on connection failure;
already-applied DDL is the success case.
"""

from __future__ import annotations

import asyncio
import sys

import clickhouse_connect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from seedbank.core.config import get_settings
from seedbank.core.logging import get_logger
from seedbank.infrastructure.analytics import (
    AnalyticsRepository,
    ClickHouseClient,
    DimSeedTypeRow,
    apply_schema,
)
from seedbank.infrastructure.db.models import SeedType

log = get_logger("seedbank.init_clickhouse")


async def _ensure_database(settings: object) -> None:
    """Connect with no database selected and ``CREATE DATABASE IF NOT EXISTS``.

    The async client expects the DB to already exist at handshake time,
    so this single bootstrap call uses the sync client against the
    ``default`` system DB. Cheap, runs once per deploy.
    """
    s = settings  # type: ignore[var-annotated]
    sync_client = clickhouse_connect.get_client(
        host=s.clickhouse_host,  # type: ignore[attr-defined]
        port=s.clickhouse_port,  # type: ignore[attr-defined]
        username=s.clickhouse_user,  # type: ignore[attr-defined]
        password=s.clickhouse_password.get_secret_value(),  # type: ignore[attr-defined]
        database="default",
        connect_timeout=10,
    )
    try:
        sync_client.command(f"CREATE DATABASE IF NOT EXISTS {s.clickhouse_database}")  # type: ignore[attr-defined]
        log.info("clickhouse.database_ensured", database=s.clickhouse_database)  # type: ignore[attr-defined]
    finally:
        sync_client.close()


async def _seed_dim_seed_types(repo: AnalyticsRepository) -> int:
    """Mirror the ``seed_types`` catalog into ``dim_seed_type``."""
    settings = get_settings()
    engine = create_async_engine(str(settings.postgres_dsn), future=True)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        async with sm() as session:
            rows = list((await session.execute(select(SeedType))).scalars().all())
        if not rows:
            log.info("clickhouse.seed_types_skipped", reason="empty_catalog")
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
        log.info("clickhouse.seed_types_synced", n=len(rows))
        return len(rows)
    finally:
        await engine.dispose()


async def main() -> int:
    settings = get_settings()
    await _ensure_database(settings)

    client = await ClickHouseClient.from_settings(settings)
    try:
        await apply_schema(client)
        repo = AnalyticsRepository(client)
        await _seed_dim_seed_types(repo)
    finally:
        await client.close()

    log.info("clickhouse.init_done")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
