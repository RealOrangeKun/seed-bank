"""Unit tests for `services.auth_service` — repos and Redis are mocked.

We avoid mocking `AsyncSession` directly; the service only calls it for
`add` / `commit` / `flush`, which we wrap in a tiny fake.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from seedbank.core.config import get_settings
from seedbank.core.exceptions import (
    AuthError,
    ConflictError,
    ForbiddenError,
    ValidationError,
)
from seedbank.core.security import hash_password
from seedbank.services.auth_service import AuthService


class _FakeSession:
    """Records `.add(...)` and `.commit()`/`.flush()` calls."""

    def __init__(self) -> None:
        self.added: list[Any] = []
        self.commits = 0
        self.flushes = 0

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1

    async def flush(self) -> None:
        self.flushes += 1

    async def rollback(self) -> None:
        pass


def _build_service(
    *,
    user_lookup: object | None = None,
    refresh_active: object | None = None,
) -> tuple[AuthService, _FakeSession, MagicMock, MagicMock, MagicMock, AsyncMock]:
    session = _FakeSession()
    users = MagicMock()
    users.get_by_email = AsyncMock(return_value=user_lookup)
    users.get_by_id_active = AsyncMock(return_value=user_lookup)
    users.get = AsyncMock(return_value=user_lookup)
    users.add = AsyncMock(side_effect=lambda u: u)
    users.touch_last_login = AsyncMock()
    users.mark_verified = AsyncMock(return_value=1)
    users.set_role = AsyncMock(return_value=1)

    refresh_tokens = MagicMock()
    refresh_tokens.add = AsyncMock(side_effect=lambda t: t)
    refresh_tokens.get_active_by_hash = AsyncMock(return_value=refresh_active)
    refresh_tokens.rotate = AsyncMock(return_value=1)
    refresh_tokens.revoke_all_for_user = AsyncMock(return_value=0)

    oauth_accounts = MagicMock()
    oauth_accounts.get_by_provider_subject = AsyncMock(return_value=None)
    oauth_accounts.find_by = AsyncMock(return_value=None)

    redis = AsyncMock()
    redis.set = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.delete = AsyncMock()

    svc = AuthService(
        session=session,  # type: ignore[arg-type]
        users=users,
        refresh_tokens=refresh_tokens,
        oauth_accounts=oauth_accounts,
        redis=redis,
        settings=get_settings(),
    )
    return svc, session, users, refresh_tokens, oauth_accounts, redis


class TestRegister:
    @pytest.mark.asyncio
    async def test_happy_path(self) -> None:
        svc, session, users, _, _, redis = _build_service(user_lookup=None)
        user, token = await svc.register(
            email="a@b.com", password="StrongPasswd1A", full_name="A B",
        )
        assert user.email == "a@b.com"
        assert user.hashed_password is not None
        assert token  # plaintext returned to caller for emailing
        users.add.assert_awaited_once()
        redis.set.assert_awaited_once()
        assert session.commits == 1

    @pytest.mark.asyncio
    async def test_rejects_weak_password(self) -> None:
        svc, *_ = _build_service(user_lookup=None)
        with pytest.raises(ValidationError):
            await svc.register(email="a@b.com", password="short", full_name=None)

    @pytest.mark.asyncio
    async def test_rejects_existing_email(self) -> None:
        existing = MagicMock(id="x", email="a@b.com")
        svc, *_ = _build_service(user_lookup=existing)
        with pytest.raises(ConflictError):
            await svc.register(
                email="a@b.com", password="StrongPasswd1A", full_name=None,
            )


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_rejects_unverified(self) -> None:
        from uuid import uuid4

        user = MagicMock(
            id=uuid4(),
            email="a@b.com",
            role="end_user",
            is_active=True,
            is_verified=False,
            hashed_password=hash_password("StrongPasswd1A"),
        )
        svc, *_ = _build_service(user_lookup=user)
        with pytest.raises(ForbiddenError):
            await svc.login(email="a@b.com", password="StrongPasswd1A")

    @pytest.mark.asyncio
    async def test_login_rejects_inactive(self) -> None:
        from uuid import uuid4

        user = MagicMock(
            id=uuid4(),
            email="a@b.com",
            role="end_user",
            is_active=False,
            is_verified=True,
            hashed_password=hash_password("StrongPasswd1A"),
        )
        svc, *_ = _build_service(user_lookup=user)
        with pytest.raises(ForbiddenError):
            await svc.login(email="a@b.com", password="StrongPasswd1A")

    @pytest.mark.asyncio
    async def test_login_rejects_bad_password(self) -> None:
        from uuid import uuid4

        user = MagicMock(
            id=uuid4(),
            email="a@b.com",
            role="end_user",
            is_active=True,
            is_verified=True,
            hashed_password=hash_password("StrongPasswd1A"),
        )
        svc, *_ = _build_service(user_lookup=user)
        with pytest.raises(AuthError):
            await svc.login(email="a@b.com", password="WrongPasswd1A")

    @pytest.mark.asyncio
    async def test_login_rejects_unknown_email(self) -> None:
        svc, *_ = _build_service(user_lookup=None)
        with pytest.raises(AuthError):
            await svc.login(email="nope@b.com", password="WhateverPwd1A")


class TestPasswordOrOauthInvariant:
    @pytest.mark.asyncio
    async def test_oauth_only_user_is_valid(self) -> None:
        # When a user has no password but has an oauth account, the invariant
        # check should pass.
        from uuid import uuid4

        from seedbank.infrastructure.db.models import User

        u = User(
            id=uuid4(), email="x@y.com", hashed_password=None,
            role="end_user", is_active=True, is_verified=True,
        )
        svc, _s, _u, _r, oauth, _redis = _build_service()
        oauth.find_by = AsyncMock(return_value=MagicMock())
        # Should not raise.
        await svc._assert_password_or_oauth(u)  # noqa: SLF001

    @pytest.mark.asyncio
    async def test_no_password_no_oauth_rejected(self) -> None:
        from uuid import uuid4

        from seedbank.infrastructure.db.models import User

        u = User(
            id=uuid4(), email="x@y.com", hashed_password=None,
            role="end_user", is_active=True, is_verified=True,
        )
        svc, *_ = _build_service()
        with pytest.raises(ValidationError):
            await svc._assert_password_or_oauth(u)  # noqa: SLF001
