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
    headers_enabled=True,
)


def install_rate_limiter(app: "FastAPI") -> None:
    """Mount the limiter on the app and register the 429 handler."""
    app.state.limiter = limiter

    async def _handler(_request: Request, exc: RateLimitExceeded):
        from fastapi.responses import JSONResponse

        retry_after = getattr(exc, "retry_after", None)
        headers = {"Retry-After": str(int(retry_after))} if retry_after else {}
        return JSONResponse(
            status_code=429,
            content={"error": "RateLimitError", "detail": str(exc.detail)},
            headers=headers,
        )

    app.add_exception_handler(RateLimitExceeded, _handler)


__all__ = ["install_rate_limiter", "limiter"]
