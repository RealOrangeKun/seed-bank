"""Sentry SDK initialisation.

Phase 9. No-op when ``SENTRY_DSN`` is unset, which is the default for the
dev compose stack and every test run. When set, we lean on Sentry's
FastAPI + Celery integrations rather than instrumenting by hand — they
already capture request context, user, and unhandled exceptions.

Sample rates default conservatively; production tunes via env. We never
capture PII (``send_default_pii=False``); request IDs already flow
through structlog so cross-system correlation does not require
Sentry-side identity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from seedbank.core.logging import get_logger

if TYPE_CHECKING:
    from seedbank.core.config import Settings

log = get_logger(__name__)

_INITIALISED = False


def init_sentry(settings: Settings) -> None:
    """Initialise Sentry once per process. No-op when DSN is unset."""
    global _INITIALISED
    if _INITIALISED:
        return
    dsn = settings.sentry_dsn.get_secret_value() if settings.sentry_dsn else None
    if not dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except Exception as exc:  # noqa: BLE001 — sentry must never crash boot
        log.warning("sentry.import_failed", error=repr(exc))
        return

    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=settings.env,
            release=f"{settings.service_name}@0.1.0",
            send_default_pii=False,
            # FastAPI/Starlette integrations otherwise capture up to 1KB of
            # request body — that includes login JSON (email + password) and
            # OAuth callback codes. ``never`` switches the body capture off
            # entirely; the structured-log request_id is enough correlation.
            max_request_body_size="never",
            before_send=_before_send,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            profiles_sample_rate=settings.sentry_profiles_sample_rate,
            integrations=[
                StarletteIntegration(),
                FastApiIntegration(),
                CeleryIntegration(),
            ],
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("sentry.init_failed", error=repr(exc))
        return

    _INITIALISED = True
    log.info("sentry.initialised", env=settings.env)


def _before_send(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    """Defensive PII scrub: drop request body even if ``max_request_body_size``
    is bypassed by an integration we don't control. Returning the event keeps
    the trace; only the body is removed."""
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)
    return event


__all__ = ["init_sentry"]
