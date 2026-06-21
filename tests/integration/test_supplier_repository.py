"""Integration tests for the Supplier repository.

Verifies the global / private split: a user only sees globals + their own
private rows, and the partial uniques actually fire.
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.infrastructure.db.enums import UserRole
from seedbank.infrastructure.db.models import Supplier, User
from seedbank.infrastructure.db.repositories import SupplierRepository

pytestmark = pytest.mark.integration


async def _seed_user(db_session: AsyncSession, email: str) -> User:
    user = User(
        email=email,
        hashed_password="bcrypt$irrelevant",
        role=UserRole.END_USER.value,
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def test_user_sees_globals_plus_own_private(db_session: AsyncSession) -> None:
    alice = await _seed_user(db_session, "alice-supp@example.com")
    bob = await _seed_user(db_session, "bob-supp@example.com")

    db_session.add_all(
        [
            Supplier(name="Acme", slug="acme", is_global=True, created_by_user_id=None),
            Supplier(
                name="Alice's Local",
                slug="alice-local",
                is_global=False,
                created_by_user_id=alice.id,
            ),
            Supplier(
                name="Bob's Local",
                slug="bob-local",
                is_global=False,
                created_by_user_id=bob.id,
            ),
        ]
    )
    await db_session.commit()

    repo = SupplierRepository(db_session)
    visible = await repo.list_visible_to(alice.id)
    names = {s.name.lower() for s in visible}
    assert "acme" in names and "alice's local" in names and "bob's local" not in names


async def test_global_xor_owner_check_constraint(db_session: AsyncSession) -> None:
    """`is_global=true` AND `created_by_user_id` set must be rejected."""
    alice = await _seed_user(db_session, "alice-xor@example.com")
    db_session.add(Supplier(name="Bad", slug="bad", is_global=True, created_by_user_id=alice.id))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()
