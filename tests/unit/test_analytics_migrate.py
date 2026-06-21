"""Unit tests for the ClickHouse DDL applier.

The runner is intentionally simple: read ``schema.sql``, split on ``;``,
execute. These tests pin both behaviors so a future refactor that adds
materialized views (with embedded SELECTs) breaks the splitter loudly
rather than silently feeding a half-statement to ClickHouse.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from seedbank.infrastructure.analytics.migrate import (
    _load_schema_sql,
    _split_statements,
    apply_schema,
)

pytestmark = pytest.mark.unit


def test_schema_sql_is_loaded_from_package() -> None:
    sql = _load_schema_sql()
    assert "fact_inference" in sql
    assert "fact_detection" in sql
    assert "fact_experiment_result" in sql
    assert "fact_scan_batch" in sql
    assert "dim_user" in sql
    assert "dim_seed_type" in sql
    assert "dim_model" in sql


def test_split_statements_drops_empties_and_whitespace() -> None:
    sql = "CREATE TABLE a (id UUID);;\n  \n  CREATE TABLE b (id UUID);"
    out = _split_statements(sql)
    assert len(out) == 2
    assert all(s.startswith("CREATE TABLE") for s in out)


def test_every_create_uses_if_not_exists() -> None:
    """The runner is idempotent only because every statement is gated."""
    sql = _load_schema_sql()
    statements = _split_statements(sql)
    create_stmts = [s for s in statements if s.lstrip().upper().startswith("CREATE")]
    for s in create_stmts:
        # ``CREATE TABLE IF NOT EXISTS`` — the seed of all idempotency.
        assert "IF NOT EXISTS" in s.upper(), s[:80]


async def test_apply_schema_executes_each_statement() -> None:
    fake = AsyncMock()
    fake.execute = AsyncMock()
    n = await apply_schema(fake)
    assert n == fake.execute.await_count
    assert n >= 7  # 3 dims + 4 facts at minimum
