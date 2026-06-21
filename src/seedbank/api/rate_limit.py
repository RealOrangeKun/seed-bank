"""Per-route rate limiting (slowapi) backed by Redis.

slowapi is a thin Starlette wrapper over `limits`. We give it a single
`Limiter` keyed by IP for unauthenticated routes; for authenticated routes
where rate-limit-by-user makes sense, the route depends on `current_user`
and uses a custom key.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request

from seedbank.api.errors import build_problem
from seedbank.core.config import get_settings

if TYPE_CHECKING:
    from fastapi import FastAPI


def _redis_uri_for_limits() -> str:
    """Build a `redis://...` URI for the `limits` library to consume.

    `limits` does not accept the `redis+async://` form; we pass the same DSN
    used by the rest of the app and rely on its sync redis client (limited to
    the few atomic commands we need) — tolerable here because slowapi's hot
    path is INCR + EXPIRE, not per-request.
    """
    return str(get_settings().redis_dsn)


limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_redis_uri_for_limits(),
    # `headers_enabled=True` requires every rate-limited route to declare an
    # explicit `response: Response` parameter so slowapi can attach
    # X-RateLimit-* headers. Without that param it raises "parameter
    # `response` must be an instance of starlette.responses.Response" on
    # the success path. We instead emit `Retry-After` ourselves from the
    # 429 handler in `install_rate_limiter`, which is the header that
    # actually matters for clients.
    headers_enabled=False,
)


def install_rate_limiter(app: "FastAPI") -> None:
    """Mount the limiter on the app and register the 429 handler.

    The 429 response shares the RFC 9457 Problem Details shape with every
    other error in the pipeline (see ``api/errors.py``). Only the
    ``Retry-After`` header is custom — clients look for the seconds-to-wait
    there, not inside the JSON body.
    """
    app.state.limiter = limiter

    async def _handler(request: Request, exc: RateLimitExceeded):
        # Compute Retry-After from the limit's window. slowapi's
        # RateLimitExceeded does not expose an `exc.retry_after`; the
        # underlying `limits.RateLimitItem.get_expiry()` returns the
        # window length in seconds (60 for `/minute`, 1 for `/second`),
        # which is the upper bound on how long a client must back off.
        retry_after_seconds: int | None = None
        limit = getattr(exc, "limit", None)
        inner = getattr(limit, "limit", None)
        if inner is not None and hasattr(inner, "get_expiry"):
            try:
                retry_after_seconds = int(inner.get_expiry())
            except (TypeError, ValueError):
                retry_after_seconds = None

        extra_headers = (
            {"Retry-After": str(retry_after_seconds)}
            if retry_after_seconds is not None
            else None
        )
        return build_problem(
            request=request,
            status_code=429,
            code="rate_limited",
            title="Too Many Requests",
            detail=str(exc.detail) if exc.detail else "Rate limit exceeded.",
            extra_headers=extra_headers,
        )

    app.add_exception_handler(RateLimitExceeded, _handler)


__all__ = ["install_rate_limiter", "limiter"]
