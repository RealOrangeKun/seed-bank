"""Unit tests for OAuth provider gating.

A provider is *enabled* iff both its client id and secret are present in
``Settings``. The ``/auth/oauth/providers`` endpoint renders one button per
configured provider, so leaving a provider's credentials unset hides it.
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from seedbank.core.config import Settings
from seedbank.infrastructure.oauth import google

pytestmark = pytest.mark.unit


def _settings(**overrides: object) -> Settings:
    # ``_env_file=None`` isolates the test from the developer's local ``.env``.
    return Settings(_env_file=None, **overrides)  # type: ignore[arg-type]


def test_google_enabled_when_both_credentials_set() -> None:
    s = _settings(
        oauth_google_client_id=SecretStr("client-id"),
        oauth_google_client_secret=SecretStr("client-secret"),
    )
    assert google.is_configured(s) is True


def test_google_disabled_when_secret_missing() -> None:
    s = _settings(oauth_google_client_id=SecretStr("client-id"))
    assert google.is_configured(s) is False


def test_google_disabled_when_credentials_unset() -> None:
    assert google.is_configured(_settings()) is False
