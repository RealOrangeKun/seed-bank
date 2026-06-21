"""User factory.

Builds a fully-validated ``User`` ORM instance with sensible, deterministic
defaults. Tests override only the fields they care about — the factory keeps
required-field invariants in one place so a new column added to ``User``
doesn't ripple through 50 test files.
"""

from __future__ import annotations

import factory
from factory import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from seedbank.core.security import hash_password
from seedbank.infrastructure.db.enums import UserRole
from seedbank.infrastructure.db.models import User
from seedbank.infrastructure.db.repositories import UserRepository

# A single, strong password reused across every factory-built user. Tests
# that need to log in import this constant rather than retyping it — keeps
# the credential out of literal strings scattered through the suite.
DEFAULT_TEST_PASSWORD = "StrongPasswd1A"

# bcrypt is intentionally slow; compute the hash exactly once per process.
_HASHED_DEFAULT = hash_password(DEFAULT_TEST_PASSWORD)


class UserFactory(factory.Factory):
    """Build (don't persist) a ``User`` ORM instance.

    Use ``UserFactory.build(...)`` for the in-memory object; persistence is
    handled by ``make_user`` below, which writes through the repository so
    we don't bypass invariants the repo enforces.
    """

    class Meta:
        model = User

    email = Faker("email")
    hashed_password = _HASHED_DEFAULT
    full_name = Faker("name")
    role = UserRole.END_USER.value
    is_active = True
    is_verified = True


async def make_user(
    session: AsyncSession,
    *,
    role: UserRole = UserRole.END_USER,
    email: str | None = None,
    is_active: bool = True,
    is_verified: bool = True,
) -> User:
    """Persist a ``User`` via the repository and commit. Returns the row.

    Tests should call this rather than instantiating ``User`` directly so
    that the bcrypt hash, role-string conversion, and commit semantics live
    in exactly one place.
    """
    user = UserFactory.build(
        role=role.value,
        is_active=is_active,
        is_verified=is_verified,
        **({"email": email} if email is not None else {}),
    )
    repo = UserRepository(session)
    await repo.add(user)
    await session.commit()
    return user
