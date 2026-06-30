"""Auth domain objects.

Plain Python — no SQLAlchemy, no FastAPI, no Pydantic. The `Role` enum mirrors
the Postgres `user_role` enum (kept in sync by hand because the DB enum lives
in `infrastructure/db/enums.py`, which the domain layer cannot import).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class Role(StrEnum):
    ADMIN = "admin"
    AI_DEVELOPER = "ai_developer"
    END_USER = "end_user"


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    """Snapshot of the actor for the current request.

    Built once per request (in `api.deps.current_user`) and passed by value
    into services. Frozen → safe to share, easy to reason about.

    Authorization is by role only (`require_role`); admins implicitly satisfy
    any role check.
    """

    id: UUID
    email: str
    role: Role
    is_active: bool
    is_verified: bool
    auth_method: str = "jwt"

    @property
    def is_admin(self) -> bool:
        return self.role is Role.ADMIN

    def has_role(self, role: Role) -> bool:
        # Admins implicitly satisfy any role check.
        return self.is_admin or self.role is role


@dataclass(frozen=True, slots=True)
class OAuthIdentity:
    """Normalized identity returned by the OAuth provider clients.

    Providers fan out to this shape so the auth service has one code path for
    "create or link a user from an OAuth callback."
    """

    provider: str
    subject: str
    email: str
    full_name: str | None = None


__all__ = ["AuthenticatedUser", "OAuthIdentity", "Role"]
