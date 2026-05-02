"""Cross-cutting middleware.

- :class:`RequestIdMiddleware` — assigns a UUIDv4 to every request and binds
  it to structlog contextvars so every log line within the request carries
  it. Echoed back on the response as ``X-Request-ID``.
- :class:`PrometheusMiddleware` — emits ``http_requests_total``,
  ``http_request_duration_seconds``, and ``http_requests_inflight`` for
  every routed request. Cardinality is bounded by labelling on the
  Starlette **route template** (``/api/v1/users/{id}``), never the raw URL.
- CORS comes from FastAPI's built-in middleware (wired in :mod:`main`)
  and uses :attr:`Settings.cors_allow_origins`.
"""

from __future__ import annotations

from time import perf_counter
from uuid import uuid4

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match

from seedbank.core.metrics import (
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS,
    HTTP_REQUESTS_INFLIGHT,
)


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


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Record HTTP timings and counts.

    The path label is the route template, not the raw path — otherwise a
    URL with a UUID per request would explode the time-series count.
    Unmatched paths (404 with no route, or pre-route shortcuts) collapse
    to ``"_unmatched"``.

    The ``/metrics`` endpoint itself is excluded because Prometheus
    scrapes it every 15s; counting those requests would dominate the
    histograms with a noise spike that has nothing to do with user traffic.
    """

    EXCLUDED_PATHS = frozenset({"/metrics"})

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        path = _route_template(request)
        method = request.method
        HTTP_REQUESTS_INFLIGHT.labels(method=method, path=path).inc()
        start = perf_counter()
        status = "5xx"  # unhandled exception path; 500 if call_next raises
        try:
            response = await call_next(request)
            status = _status_class(response.status_code)
            return response
        finally:
            HTTP_REQUESTS_INFLIGHT.labels(method=method, path=path).dec()
            HTTP_REQUEST_DURATION.labels(method=method, path=path).observe(
                perf_counter() - start
            )
            HTTP_REQUESTS.labels(method=method, path=path, status=status).inc()


def _status_class(code: int) -> str:
    """Bucket status codes into ``2xx``/``3xx``/``4xx``/``5xx``.

    Counting per exact status code multiplies cardinality without changing
    the dashboards anyone actually builds (rate by class, not by code).
    """
    if 200 <= code < 300:
        return "2xx"
    if 300 <= code < 400:
        return "3xx"
    if 400 <= code < 500:
        return "4xx"
    return "5xx"


def _route_template(request: Request) -> str:
    """Resolve the request path to its route template, or ``"_unmatched"``.

    Starlette doesn't expose a public helper; we re-walk the router. A
    ``Match.FULL`` always wins. Failing that, a ``Match.PARTIAL`` (path
    matches but the method doesn't — the 405 path) keeps the route
    template so dashboards can still attribute the 4xx to the right
    endpoint. Only when *no* route matches at all do we collapse to
    ``"_unmatched"``.
    """
    router = request.scope.get("router")
    if router is None:
        return "_unmatched"
    partial_path: str | None = None
    for route in router.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return getattr(route, "path", "_unmatched")
        if match == Match.PARTIAL and partial_path is None:
            partial_path = getattr(route, "path", None)
    return partial_path or "_unmatched"
