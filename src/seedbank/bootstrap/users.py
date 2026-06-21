"""Idempotent demo-user bootstrap.

The CLI under ``scripts/seed_dev.py`` chooses *which* users to seed and
where the passwords come from. This module just performs the upsert in
the supplied session.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.dialects.postgresql import insert as pg_insert

from seedbank.core.ids import uuid7
from seedbank.core.logging import get_logger
from seedbank.core.security import hash_password
from seedbank.infrastructure.db.enums import UserRole
from seedbank.infrastructure.db.models import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class DemoUserSpec:
    """One demo user the CLI wants to ensure exists."""

    email: str
    role: UserRole
    password: str
    full_name: str | None = None


async def bootstrap_users(
    session: AsyncSession, specs: list[DemoUserSpec]
) -> int:
    """Upsert (insert-if-missing) the supplied users. Returns rows inserted.

    Idempotency uses Postgres ``INSERT ... ON CONFLICT DO NOTHING`` keyed
    on the unique ``users.email``. Existing rows are intentionally NOT
    updated — re-running must not clobber a password that's been rotated
    or a role change made by an admin.

    Passwords are hashed via :func:`seedbank.core.security.hash_password`,
    which enforces the password policy. Plaintext never touches the DB or
    the logs.
    """
    if not specs:
        return 0
    rows = [
        {
            "id": uuid7(),
            "email": spec.email,
            "hashed_password": hash_password(spec.password),
            "full_name": spec.full_name,
            "role": spec.role.value,
            "is_active": True,
            "is_verified": True,
        }
        for spec in specs
    ]
    stmt = (
        pg_insert(User)
        .values(rows)
        .on_conflict_do_nothing(index_elements=[User.email])
    )
    result = await session.execute(stmt)
    inserted = result.rowcount or 0
    log.info("bootstrap.users", requested=len(rows), inserted=inserted)
    return inserted
