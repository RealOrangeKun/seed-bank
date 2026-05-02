"""Seed the dev database with the bare minimum to demo + test the platform.

Idempotent: running it twice is a no-op against any rows that already exist.
We use ``INSERT ... ON CONFLICT DO NOTHING`` keyed on the unique columns
(``users.email``, ``seed_types.code``) — atomic, race-safe, and importantly
does **not** clobber rows that an admin or curator has since modified
(rotated passwords, retuned thresholds, etc.). If you need to update the
catalog, write a separate script; this one is a one-way bootstrap.

What it seeds:

1. Three demo users — admin, ai_developer, end_user — with bcrypt-hashed
   passwords. Defaults satisfy the password policy enforced by
   ``seedbank.core.security.hash_password``; override per-role via the
   ``SEED_*_PASSWORD`` env vars before invoking.
2. Three seed types in the catalog: coffee, maize, lentil — each with a
   sensible default confidence threshold of ``0.5000``.
3. Mirrors the seed-type catalog into ClickHouse ``dim_seed_type`` by
   delegating to ``scripts.init_clickhouse.main`` (already idempotent).

Usage::

    python -m scripts.seed_dev

Invoked by ``make seed`` (see Makefile).
"""

from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from seedbank.core.config import get_settings
from seedbank.core.ids import uuid7
from seedbank.core.logging import get_logger
from seedbank.core.security import hash_password
from seedbank.infrastructure.db.enums import UserRole
from seedbank.infrastructure.db.models import SeedType, User

log = get_logger("seedbank.seed_dev")


# ── Demo data ────────────────────────────────────────────────────────────────

# (email, role, password env var, fallback password)
# Fallbacks satisfy the password policy: ≥ 12 chars, upper + lower + digit.
# They are deliberately *not* secret — anyone running ``make seed`` is on a
# dev machine and is expected to rotate or override via env vars.
_DEMO_USERS: tuple[tuple[str, UserRole, str, str, str], ...] = (
    ("admin@seedbank.dev", UserRole.ADMIN, "SEED_ADMIN_PASSWORD", "AdminDemo123!", "Admin Demo"),
    (
        "ai-dev@seedbank.dev",
        UserRole.AI_DEVELOPER,
        "SEED_AI_DEV_PASSWORD",
        "AiDevDemo123!",
        "AI Dev Demo",
    ),
    (
        "user@seedbank.dev",
        UserRole.END_USER,
        "SEED_END_USER_PASSWORD",
        "UserDemo123!",
        "End User Demo",
    ),
)

# (code, display_name, default_confidence_threshold_str)
_SEED_TYPES: tuple[tuple[str, str, str], ...] = (
    ("coffee", "Coffee", "0.5000"),
    ("maize", "Maize", "0.5000"),
    ("lentil", "Lentil", "0.5000"),
)


# ── Workers ──────────────────────────────────────────────────────────────────


async def _seed_users(session_maker: async_sessionmaker) -> int:
    """Upsert (insert-if-missing) the demo users. Returns rows inserted."""
    used_defaults: list[str] = []
    rows: list[dict[str, object]] = []
    for email, role, env_var, default_pwd, full_name in _DEMO_USERS:
        password = os.environ.get(env_var) or default_pwd
        if env_var not in os.environ:
            used_defaults.append(env_var)
        rows.append(
            {
                "id": uuid7(),
                "email": email,
                "hashed_password": hash_password(password),
                "full_name": full_name,
                "role": role.value,
                "is_active": True,
                "is_verified": True,
            }
        )

    async with session_maker() as session, session.begin():
        stmt = pg_insert(User).values(rows).on_conflict_do_nothing(
            index_elements=[User.email]
        )
        result = await session.execute(stmt)

    inserted = result.rowcount or 0
    if used_defaults:
        # NEVER log the actual password values. Listing the env vars is
        # enough to nudge the operator to set them on a shared machine.
        log.warning(
            "seed_dev.using_default_passwords",
            unset_env_vars=used_defaults,
        )
    log.info("seed_dev.users_upserted", requested=len(rows), inserted=inserted)
    return inserted


async def _seed_seed_types(session_maker: async_sessionmaker) -> int:
    """Upsert the seed-type catalog. Returns rows inserted."""
    rows = [
        {
            "id": uuid7(),
            "code": code,
            "display_name": display_name,
            "default_confidence_threshold": threshold,
        }
        for code, display_name, threshold in _SEED_TYPES
    ]

    async with session_maker() as session, session.begin():
        stmt = pg_insert(SeedType).values(rows).on_conflict_do_nothing(
            index_elements=[SeedType.code]
        )
        result = await session.execute(stmt)

    inserted = result.rowcount or 0
    log.info("seed_dev.seed_types_upserted", requested=len(rows), inserted=inserted)
    return inserted


# ── Entry point ──────────────────────────────────────────────────────────────


async def main() -> int:
    settings = get_settings()
    # Per-script engine (mirrors ``scripts/init_clickhouse.py``). Do NOT reuse
    # the API's ``@lru_cache``-d engine — its connections are bound to the
    # API process's event loop, not this script's.
    engine = create_async_engine(str(settings.postgres_dsn), future=True)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        users_inserted = await _seed_users(sm)
        seed_types_inserted = await _seed_seed_types(sm)
    finally:
        await engine.dispose()

    # Mirror the freshly-seeded ``seed_types`` into ClickHouse
    # ``dim_seed_type`` so fact-table joins resolve immediately. The
    # CH script opens its own engines — must run after our PG engine
    # is disposed (above) to avoid pool starvation under tight limits.
    from scripts.init_clickhouse import main as ch_main

    rc = await ch_main()
    if rc != 0:
        log.error("seed_dev.clickhouse_init_failed", rc=rc)
        return rc

    log.info(
        "seed_dev.done",
        users_inserted=users_inserted,
        seed_types_inserted=seed_types_inserted,
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
