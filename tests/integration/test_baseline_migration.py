"""Integration test for the Alembic baseline migration.

Spins up a real Postgres via testcontainers, runs `upgrade head` →
`downgrade base` → `upgrade head`, and confirms the schema reaches the
expected table count both times.

Marked `integration` so the unit-test gate doesn't pull a container.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from testcontainers.postgres import PostgresContainer

from seedbank.infrastructure.db import models  # noqa: F401  — register tables
from seedbank.infrastructure.db.base import Base

pytestmark = pytest.mark.integration

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TABLES = len(Base.metadata.tables)  # 18 from the schema spec


def _alembic_config(sync_dsn: str) -> Config:
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", sync_dsn)
    return cfg


def test_baseline_up_down_up() -> None:
    with PostgresContainer("postgres:16-alpine") as pg:
        # Bootstrap citext / pg_trgm — the prod DB gets these via init.sql.
        sync_dsn = pg.get_connection_url()  # postgresql+psycopg2://...
        # The project pins to psycopg (v3) for sync usage; rewrite the driver.
        sync_dsn = sync_dsn.replace("postgresql+psycopg2://", "postgresql+psycopg://")

        engine = create_engine(sync_dsn, future=True)
        with engine.begin() as conn:
            conn.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS "citext"')
            conn.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')

        # Alembic env.py reads from Settings.postgres_dsn — override via env.
        async_dsn = sync_dsn.replace("postgresql+psycopg://", "postgresql+asyncpg://")
        os.environ["POSTGRES_DSN"] = async_dsn

        # Force Settings re-evaluation to pick up the env var.
        from seedbank.core.config import get_settings

        get_settings.cache_clear()

        cfg = _alembic_config(sync_dsn)

        command.upgrade(cfg, "head")
        with engine.connect() as conn:
            assert len(inspect(conn).get_table_names()) - 1 >= EXPECTED_TABLES
            # -1 for alembic_version. ">=" because future migrations add tables.

        command.downgrade(cfg, "base")
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names()) - {"alembic_version"}
            assert tables == set(), f"downgrade left tables: {tables}"

        command.upgrade(cfg, "head")
        with engine.connect() as conn:
            assert len(inspect(conn).get_table_names()) - 1 >= EXPECTED_TABLES

        engine.dispose()
