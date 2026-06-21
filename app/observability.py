"""Observability: structured JSON logging + request-ID / timing middleware.

Keeps the FastAPI app production-friendly without external deps:
- one JSON log line per request (method, path, status, duration, request_id)
- an X-Request-ID echoed/generated per request, available as request.state.request_id
- an X-Process-Time-Ms header with the server-side duration
"""
import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Correlation id available anywhere during a request (e.g. inside log records).
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class JsonLogFormatter(logging.Formatter):
    """Render log records as single-line JSON with the active request id."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        # Attach structured extras when present.
        for key in ("method", "path", "status", "duration_ms", "client"):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> logging.Logger:
    """Configure root + app logger to emit structured JSON to stdout (idempotent)."""
    root = logging.getLogger()
    root.setLevel(level)
    # Replace any default handlers with our JSON handler.
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    root.addHandler(handler)
    # Quiet uvicorn's access logger (we log requests ourselves).
    logging.getLogger("uvicorn.access").disabled = True
    return logging.getLogger("seedbank")


logger = logging.getLogger("seedbank")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a request id, time the request, log it, and set response headers."""

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        token = request_id_ctx.set(req_id)
        request.state.request_id = req_id
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            client = request.client.host if request.client else None
            logger.info(
                "request",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": status,
                    "duration_ms": duration_ms,
                    "client": client,
                },
            )
            try:
                # Headers can only be set if the response object exists.
                response.headers["X-Request-ID"] = req_id
                response.headers["X-Process-Time-Ms"] = str(duration_ms)
            except Exception:
                pass
            request_id_ctx.reset(token)
