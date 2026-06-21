"""Unit tests for ``core/sentry.py``.

The Sentry bootstrap is small but security-load-bearing:

* PII opt-out (``send_default_pii=False``).
* Request body cap (``max_request_body_size="never"``) — login JSON and
  OAuth callback codes must never reach Sentry.
* Defensive ``before_send`` hook drops ``request.data`` even if an
  integration we don't control circumvents the body cap.
* Idempotent — must call ``sentry_sdk.init`` exactly once per process.

The ``sentry-sdk`` package may not be installed in the unit-test venv
(it's an optional dep for the API image). We inject lightweight fakes
into ``sys.modules`` before ``init_sentry`` does its lazy import, so
the module's import-failure branch is never taken in these tests.
"""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest
from pydantic import SecretStr

from seedbank.core import sentry as sentry_module
from seedbank.core.config import Settings

pytestmark = pytest.mark.unit


def _settings(*, dsn: str | None) -> Settings:
    return cast(
        "Settings",
        SimpleNamespace(
            sentry_dsn=SecretStr(dsn) if dsn is not None else None,
            env="test",
            service_name="seedbank-api",
            sentry_traces_sample_rate=0.1,
            sentry_profiles_sample_rate=0.0,
        ),
    )


def _install_fake_sentry_sdk(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Inject a fake ``sentry_sdk`` (and the three integration submodules
    the module imports) into ``sys.modules`` so ``init_sentry``'s lazy
    import path resolves without the real package."""
    fake_sentry = ModuleType("sentry_sdk")
    fake_sentry.init = MagicMock()  # type: ignore[attr-defined]

    celery_mod = ModuleType("sentry_sdk.integrations.celery")
    celery_mod.CeleryIntegration = MagicMock()  # type: ignore[attr-defined]
    fastapi_mod = ModuleType("sentry_sdk.integrations.fastapi")
    fastapi_mod.FastApiIntegration = MagicMock()  # type: ignore[attr-defined]
    starlette_mod = ModuleType("sentry_sdk.integrations.starlette")
    starlette_mod.StarletteIntegration = MagicMock()  # type: ignore[attr-defined]
    integrations_mod = ModuleType("sentry_sdk.integrations")

    monkeypatch.setitem(sys.modules, "sentry_sdk", fake_sentry)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations", integrations_mod)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.celery", celery_mod)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.fastapi", fastapi_mod)
    monkeypatch.setitem(sys.modules, "sentry_sdk.integrations.starlette", starlette_mod)
    init_mock: MagicMock = fake_sentry.init
    return init_mock


@pytest.fixture(autouse=True)
def _reset_sentry_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """``_INITIALISED`` is a module-global that survives across tests; reset
    so each test starts from a clean state."""
    monkeypatch.setattr(sentry_module, "_INITIALISED", False)


def test_init_sentry_noop_without_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    """No DSN → ``sentry_sdk.init`` must not be called (default dev path)."""
    fake_init = _install_fake_sentry_sdk(monkeypatch)

    sentry_module.init_sentry(_settings(dsn=None))

    fake_init.assert_not_called()
    assert sentry_module._INITIALISED is False


def test_init_sentry_passes_pii_and_body_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When DSN set, ``init`` is called once with the security-relevant
    flags."""
    fake_init = _install_fake_sentry_sdk(monkeypatch)

    sentry_module.init_sentry(_settings(dsn="https://public@sentry.example/1"))

    fake_init.assert_called_once()
    kwargs = fake_init.call_args.kwargs
    assert kwargs["send_default_pii"] is False
    assert kwargs["max_request_body_size"] == "never"
    assert callable(kwargs["before_send"])
    assert kwargs["dsn"] == "https://public@sentry.example/1"
    assert sentry_module._INITIALISED is True


def test_before_send_drops_request_data() -> None:
    """The defensive scrub: even if an integration sneaks a request body
    past ``max_request_body_size``, ``before_send`` removes it."""
    event = {
        "request": {
            "url": "/auth/login",
            "method": "POST",
            "data": {"email": "victim@example.com", "password": "leaked"},
        },
        "level": "error",
    }
    out = sentry_module._before_send(event, {})
    assert "data" not in out["request"]
    # The rest of the request context survives so the trace is still useful.
    assert out["request"]["url"] == "/auth/login"
    assert out["level"] == "error"


def test_before_send_tolerates_missing_request() -> None:
    """A bare event without ``request`` must round-trip unchanged."""
    event = {"level": "error", "logger": "seedbank"}
    out = sentry_module._before_send(event, {})
    assert out == {"level": "error", "logger": "seedbank"}


def test_init_sentry_is_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Two consecutive calls must invoke ``sentry_sdk.init`` exactly once
    — the global flag prevents double-init from leaking integrations."""
    fake_init = _install_fake_sentry_sdk(monkeypatch)

    sentry_module.init_sentry(_settings(dsn="https://public@sentry.example/1"))
    sentry_module.init_sentry(_settings(dsn="https://public@sentry.example/1"))

    assert fake_init.call_count == 1
