"""Thin CLI wrapper that seeds the dev database with demo data.

Idempotent: re-running is a no-op against any rows that already exist.
The actual upsert logic lives in :mod:`seedbank.bootstrap` so it can be
unit-tested without spinning up a stack.

What it seeds:

1. Three demo users — admin, ai_developer, end_user. Passwords come from
   ``SEED_*_PASSWORD`` env vars. If any are missing the script refuses
   to run unless ``SEED_ALLOW_DEMO_DEFAULTS=1`` is set explicitly — that
   way an accidental ``make seed`` against a real environment cannot
   silently install a known-default credential.
2. Three seed types: coffee, maize, lentil — each at confidence 0.5000.
3. Three global demo suppliers, so the frontend dropdowns aren't empty.
4. Mirrors the seed-type catalog into ClickHouse ``dim_seed_type`` via
   :func:`seedbank.bootstrap.dwh.mirror_seed_types_to_dwh`.

Usage::

    SEED_ADMIN_PASSWORD=...  SEED_AI_DEV_PASSWORD=...  \
    SEED_END_USER_PASSWORD=...  python -m scripts.seed_dev

    # Or, for local dev only:
    SEED_ALLOW_DEMO_DEFAULTS=1 python -m scripts.seed_dev
"""

from __future__ import annotations

import asyncio
import os
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from seedbank.bootstrap import (
    DemoUserSpec,
    GlobalSupplierSpec,
    SeedTypeSpec,
    bootstrap_clickhouse,
    bootstrap_seed_types,
    bootstrap_suppliers,
    bootstrap_users,
)
from seedbank.core.config import get_settings
from seedbank.core.logging import get_logger
from seedbank.infrastructure.db.enums import UserRole

log = get_logger("seedbank.seed_dev")


# (env_var, default_for_demo, role, email, full_name)
# Defaults satisfy the password policy but are intentionally well-known —
# the script refuses to use them unless SEED_ALLOW_DEMO_DEFAULTS=1.
_DEMO_USERS: tuple[tuple[str, str, UserRole, str, str], ...] = (
    (
        "SEED_ADMIN_PASSWORD",
        "AdminDemo123!",
        UserRole.ADMIN,
        "admin@seedbank.dev",
        "Admin Demo",
    ),
    (
        "SEED_AI_DEV_PASSWORD",
        "AiDevDemo123!",
        UserRole.AI_DEVELOPER,
        "ai-dev@seedbank.dev",
        "AI Dev Demo",
    ),
    (
        "SEED_END_USER_PASSWORD",
        "UserDemo123!",
        UserRole.END_USER,
        "user@seedbank.dev",
        "End User Demo",
    ),
)

_SEED_TYPES: tuple[SeedTypeSpec, ...] = (
    SeedTypeSpec(code="coffee", display_name="Coffee"),
    SeedTypeSpec(code="maize", display_name="Maize"),
    SeedTypeSpec(code="lentil", display_name="Lentil"),
)

_SUPPLIERS: tuple[GlobalSupplierSpec, ...] = (
    GlobalSupplierSpec(name="Kenya Seed Co"),
    GlobalSupplierSpec(name="East African Seed"),
    GlobalSupplierSpec(name="Demo Agritech"),
)


def _build_user_specs() -> tuple[list[DemoUserSpec], list[str]]:
    """Resolve passwords from env. Returns (specs, names_using_default)."""
    specs: list[DemoUserSpec] = []
    used_default_for: list[str] = []
    for env_var, fallback, role, email, full_name in _DEMO_USERS:
        # `or None`: an unset var is None, but compose passes `${SEED_*:-}` as an
        # empty string — treat both as "use the demo default" rather than seeding
        # an empty password (which fails the 12-char policy).
        password = os.environ.get(env_var) or None
        if password is None:
            password = fallback
            used_default_for.append(env_var)
        specs.append(DemoUserSpec(email=email, role=role, password=password, full_name=full_name))
    return specs, used_default_for


async def main() -> int:
    user_specs, used_default_for = _build_user_specs()

    if used_default_for and os.environ.get("SEED_ALLOW_DEMO_DEFAULTS") != "1":
        # Refuse to seed known-default credentials unless the operator has
        # explicitly opted in. This guard exists so that an accidental
        # ``make seed`` against a non-dev env cannot silently install a
        # credential whose password is in this file.
        log.error(
            "seed_dev.refusing_defaults",
            unset_env_vars=used_default_for,
            hint=(
                "set the listed SEED_*_PASSWORD env vars, or "
                "SEED_ALLOW_DEMO_DEFAULTS=1 if this is a local dev box"
            ),
        )
        return 2

    if used_default_for:
        log.warning("seed_dev.using_default_passwords", unset_env_vars=used_default_for)

    settings = get_settings()
    engine = create_async_engine(str(settings.postgres_dsn), future=True)
    sm = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        async with sm() as session, session.begin():
            users_inserted = await bootstrap_users(session, user_specs)
            seed_types_inserted = await bootstrap_seed_types(session, list(_SEED_TYPES))
            suppliers_inserted = await bootstrap_suppliers(session, list(_SUPPLIERS))
    finally:
        await engine.dispose()

    # Mirror the seed-type catalog into ClickHouse. ``bootstrap_clickhouse``
    # is the same code path ``init_clickhouse.py`` uses — DRY across the
    # CLIs without script-imports-script coupling.
    await bootstrap_clickhouse(settings)

    log.info(
        "seed_dev.done",
        users_inserted=users_inserted,
        seed_types_inserted=seed_types_inserted,
        suppliers_inserted=suppliers_inserted,
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
