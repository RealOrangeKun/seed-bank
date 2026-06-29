"""Pydantic v2 DTOs for the auth + user + api-key endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from seedbank.domain.user import Role

# ── Auth ─────────────────────────────────────────────────────────────────────


class RegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: Annotated[str, Field(min_length=12, max_length=128)]
    full_name: Annotated[str | None, Field(default=None, max_length=255)] = None


class BootstrapAdminIn(BaseModel):
    """Payload for ``POST /auth/bootstrap-admin``.

    The ``bootstrap_token`` field is a shared secret rotated out of the
    environment after first-admin creation; the password rules match
    ``RegisterIn`` so the resulting admin can immediately log in.
    """

    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: Annotated[str, Field(min_length=12, max_length=128)]
    full_name: Annotated[str | None, Field(default=None, max_length=255)] = None
    bootstrap_token: Annotated[str, Field(min_length=1, max_length=512)]


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=256)]


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105
    expires_in: int


class RefreshIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: Annotated[str, Field(min_length=1, max_length=4096)]


class LogoutIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: Annotated[str, Field(min_length=1, max_length=4096)]


class VerifyEmailIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: Annotated[str, Field(min_length=1, max_length=512)]


class PasswordChangeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: Annotated[str, Field(min_length=1, max_length=256)]
    new_password: Annotated[str, Field(min_length=12, max_length=128)]


class MessageOut(BaseModel):
    message: str


# ── Users ────────────────────────────────────────────────────────────────────


class MeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str | None = None
    role: Role
    is_active: bool
    is_verified: bool
    last_login_at: datetime | None = None
    created_at: datetime | None = None


class UserListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str | None = None
    role: Role
    is_active: bool
    is_verified: bool


class RoleUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Role


# ── API keys ─────────────────────────────────────────────────────────────────


class ApiKeyCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=120)]
    scopes: Annotated[list[str], Field(default_factory=list, max_length=32)]
    expires_at: datetime | None = None


class ApiKeyOut(BaseModel):
    """Returned on **creation only**. The plaintext `key` is included exactly
    once and never retrievable again."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    prefix: str
    scopes: list[str]
    created_at: datetime
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None
    key: str | None = None


__all__ = [
    "ApiKeyCreateIn",
    "ApiKeyOut",
    "LoginIn",
    "LogoutIn",
    "MeOut",
    "MessageOut",
    "PasswordChangeIn",
    "RefreshIn",
    "RegisterIn",
    "RoleUpdateIn",
    "TokenPair",
    "UserListOut",
    "VerifyEmailIn",
]
