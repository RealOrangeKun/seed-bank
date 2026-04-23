"""E2E fixtures: token-by-role helpers built on the integration ``app_client``.

The top-level conftest provides ``app_client`` (FastAPI app wired to the
testcontainer Postgres + fakeredis); these fixtures layer the auth-flow
helpers — provision a user, hit ``/auth/login``, hand back a bearer token
— that every endpoint test needs.

Lifting these into a conftest kills the ``_seed_admin`` / ``_login``
duplication the testing-skill audit flagged.

The first admin is created through the real HTTP boundary
(``POST /auth/bootstrap-admin``) so the e2e tier doesn't bypass the API.
Non-admin roles are still seeded via the repository because the natural
HTTP path (``register`` → ``verify-email`` → ``login``) requires
intercepting the verification token from a log line, and the
registration flow is exercised separately by ``test_auth_flow.py``.
"""

from __future__ import annotations

import os

# Set BEFORE any seedbank import so `Settings()` picks it up; the
# top-level ``async_engine`` fixture also calls
# ``get_settings.cache_clear()`` after the testcontainer DSN is set,
# which guarantees the bootstrap token is visible to the app under test.
# Settings has no env_prefix, so the env var is just ``BOOTSTRAP_TOKEN``.
TEST_BOOTSTRAP_TOKEN = "test-bootstrap-secret-do-not-ship"  # noqa: S105 — fixture
os.environ.setdefault("BOOTSTRAP_TOKEN", TEST_BOOTSTRAP_TOKEN)


from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from seedbank.infrastructure.db.enums import UserRole
from seedbank.infrastructure.db.models import User
from tests.conftest import _truncate_all_tables
from tests.factories import DEFAULT_TEST_PASSWORD, make_user


@dataclass(slots=True, frozen=True)
class SeededUser:
    """A user the e2e harness has provisioned and logged in on behalf of."""

    user: User | None  # None when bootstrapped via HTTP — only the email is needed
    email: str
    token: str


SeedAndLogin = Callable[..., Awaitable[SeededUser]]


# ── Cross-tier hygiene (mirrored in tests/integration/conftest.py) ──────────
#
# Pytest's conftest discovery is hierarchical, not lateral — fixtures
# defined under ``tests/integration/conftest.py`` are NOT visible to e2e
# tests. The slowapi limiter reset has to live in both tiers; consolidating
# it under ``tests/conftest.py`` would force unit tests (which have no
# Redis access) to wait through connect-retry timeouts on every test.


@pytest_asyncio.fixture(autouse=True)
async def _truncate_db(async_engine: AsyncEngine) -> None:
    """TRUNCATE every user table before every e2e test (mirrors the
    fixture in ``tests/integration/conftest.py``)."""
    await _truncate_all_tables(async_engine)


@pytest_asyncio.fixture(autouse=True)
async def _reset_rate_limiter() -> None:
    """Clear the slowapi Limiter singleton between tests; see the matching
    fixture in ``tests/integration/conftest.py`` for the rationale."""
    from limits.errors import StorageError
    from redis.exceptions import ConnectionError as RedisConnectionError

    from seedbank.api.rate_limit import limiter

    try:
        limiter.reset()
    except (StorageError, RedisConnectionError):
        pass


# ── Auth helpers ───────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def admin(app_client: AsyncClient) -> SeededUser:
    """First-admin via the real ``POST /auth/bootstrap-admin`` endpoint.

    Goes through the full HTTP boundary — auth handler, password policy,
    audit log, the lot. Solves the chicken-and-egg cleanly: each test
    starts with a TRUNCATEd DB, so the bootstrap endpoint always sees
    "no admin yet" and succeeds.
    """
    email = "admin@e.com"
    r = await app_client.post(
        "/api/v1/auth/bootstrap-admin",
        json={
            "email": email,
            "password": DEFAULT_TEST_PASSWORD,
            "full_name": "E2E Admin",
            "bootstrap_token": TEST_BOOTSTRAP_TOKEN,
        },
    )
    assert r.status_code == 201, r.text

    login = await app_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": DEFAULT_TEST_PASSWORD},
    )
    assert login.status_code == 200, login.text
    return SeededUser(user=None, email=email, token=login.json()["data"]["access_token"])


@pytest_asyncio.fixture
async def seed_and_login(
    app_client: AsyncClient, db_session: AsyncSession
) -> SeedAndLogin:
    """Repository-backed user provisioning for non-admin roles.

    The HTTP register flow requires capturing a verification token from
    log output, which is brittle for a setup helper. The bootstrap-admin
    fixture above handles the genuine chicken-and-egg case; this helper
    fast-paths the rest.
    """

    async def _factory(role: UserRole, email: str = "user@e.com") -> SeededUser:
        user = await make_user(db_session, role=role, email=email)
        r = await app_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": DEFAULT_TEST_PASSWORD},
        )
        assert r.status_code == 200, r.text
        return SeededUser(
            user=user, email=email, token=r.json()["data"]["access_token"]
        )

    return _factory


@pytest_asyncio.fixture
async def ai_dev(seed_and_login: SeedAndLogin) -> SeededUser:
    return await seed_and_login(UserRole.AI_DEVELOPER, email="aidev@e.com")


@pytest_asyncio.fixture
async def end_user(seed_and_login: SeedAndLogin) -> SeededUser:
    return await seed_and_login(UserRole.END_USER, email="enduser@e.com")


def auth_header(token: str) -> dict[str, str]:
    """Convenience: ``{"Authorization": f"Bearer {token}"}``."""
    return {"Authorization": f"Bearer {token}"}
