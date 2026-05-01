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
    return (
        files("seedbank.infrastructure.analytics")
        .joinpath("schema.sql")
        .read_text(
            encoding="utf-8",
        )
    )


def _strip_line_comments(sql: str) -> str:
    """Drop every ``--`` line comment from the SQL.

    Done before splitting on ``;`` because semicolons inside comments
    (e.g. an English sentence in the file's header block) would
    otherwise become spurious statement boundaries. This is a
    line-oriented strip — block comments and string literals would need
    real tokenisation, but the schema file uses neither.
    """
    out: list[str] = []
    for line in sql.splitlines():
        # ``rstrip`` first so a trailing comment on a code line ('FOO; -- x')
        # is dropped; then drop full-line comments.
        cut = line.split("--", 1)[0].rstrip()
        if cut:
            out.append(cut)
    return "\n".join(out)


def _split_statements(sql: str) -> list[str]:
    """Strip line comments, then split on ``;`` and drop empty chunks.

    Naive ``;``-split would be enough on its own except that the schema
    file's header comment contains an English sentence with a semicolon
    in it. Stripping line comments first sidesteps that without needing
    a full SQL tokeniser. The schema file deliberately avoids
    semicolons in string literals so this remains sufficient.
    """
    cleaned = _strip_line_comments(sql)
    return [stmt.strip() for stmt in cleaned.split(";") if stmt.strip()]


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
