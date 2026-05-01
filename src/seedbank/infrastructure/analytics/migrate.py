"""Idempotent applier for the ClickHouse star-schema DDL.

ClickHouse doesn't ship a first-class migration tool that fits our
``alembic``-style workflow, so we keep things simple: ``schema.sql`` next
to this module is the source of truth, every statement uses
``CREATE TABLE IF NOT EXISTS``, and the runner just splits and executes.

Reapplying is safe — that's the contract — so ``init_clickhouse.py`` can
run on every deploy.
"""

from __future__ import annotations

from importlib.resources import files

from seedbank.core.logging import get_logger
from seedbank.infrastructure.analytics.clickhouse_client import ClickHouseClient

log = get_logger(__name__)


def _load_schema_sql() -> str:
    """Read the bundled ``schema.sql`` so the package works inside a wheel."""
    return files("seedbank.infrastructure.analytics").joinpath("schema.sql").read_text(
        encoding="utf-8",
    )


def _split_statements(sql: str) -> list[str]:
    """Naive ``;``-split. The schema file deliberately avoids semicolons in
    string literals so this is enough — extending it later (e.g. for
    materialized views with embedded SELECTs) is fine because each
    ``CREATE`` here is one statement that ends on ``;``."""
    return [stmt.strip() for stmt in sql.split(";") if stmt.strip()]


async def apply_schema(client: ClickHouseClient) -> int:
    """Apply ``schema.sql`` against the configured database.

    Returns the number of statements executed. Caller is expected to have
    confirmed the database exists (``CREATE DATABASE IF NOT EXISTS ...``)
    — that's the responsibility of the bootstrap script which runs as
    the privileged user, not the API.
    """
    statements = _split_statements(_load_schema_sql())
    for stmt in statements:
        await client.execute(stmt)
    log.info("clickhouse.schema_applied", n_statements=len(statements))
    return len(statements)


__all__ = ["apply_schema"]
