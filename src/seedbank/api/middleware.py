"""Cross-cutting middleware.

- `RequestIdMiddleware` — assigns a UUIDv4 to every request and binds it to
  structlog contextvars so every log line within the request carries it.
  Echoed back on the response as `X-Request-ID`.
- CORS comes from FastAPI's built-in middleware (wired in `main.py`) and uses
  `Settings.cors_allow_origins`.
"""

from __future__ import annotations

from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIdMiddleware(BaseHTTPMiddleware):
    HEADER = "X-Request-ID"

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        rid = request.headers.get(self.HEADER) or uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=rid, path=request.url.path)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers[self.HEADER] = rid
        return response
