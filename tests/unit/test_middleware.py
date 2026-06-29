"""Unit tests for ``api/middleware.py``.

Two units under test:

* :func:`_route_template` — must round-trip ``Match.FULL`` to the route
  template, fall through ``Match.PARTIAL`` (method-mismatch / 405) without
  collapsing to ``"_unmatched"``, and degrade gracefully when the scope
  has no router.
* :class:`PrometheusMiddleware` — exception path keeps the inflight gauge
  honest, observes the histogram exactly once, and ticks the counter with
  ``status="5xx"``. The ``/metrics`` self-exclusion is enforced too.

Counter assertions read deltas (``metric._value.get()`` before/after) —
the registry is process-global, so absolute values are noise.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Match, Route

from seedbank.api.middleware import PrometheusMiddleware, _route_template
from seedbank.core import metrics

pytestmark = pytest.mark.unit


# ── _route_template ───────────────────────────────────────────────────────


def _make_request(method: str, path: str, router: object | None = None) -> Request:
    scope: dict[str, object] = {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        "root_path": "",
    }
    if router is not None:
        scope["router"] = router
    return Request(scope)


async def _ok(_req: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def test_route_template_returns_path_on_full_match() -> None:
    route = Route("/healthz", _ok, methods=["GET"])
    router = Starlette(routes=[route]).router
    request = _make_request("GET", "/healthz", router=router)

    assert _route_template(request) == "/healthz"


def test_route_template_returns_unmatched_when_no_route_matches() -> None:
    route = Route("/foo", _ok, methods=["GET"])
    router = Starlette(routes=[route]).router
    request = _make_request("GET", "/totally-unknown", router=router)

    assert _route_template(request) == "_unmatched"


def test_route_template_uses_partial_match_on_method_mismatch() -> None:
    """Match.PARTIAL fires when the path matches but the method doesn't —
    the 405 branch. Backend agent's revision keeps the route template
    instead of collapsing to _unmatched so dashboards can still attribute
    the 4xx to the right endpoint."""
    route = Route("/foo", _ok, methods=["GET"])
    router = Starlette(routes=[route]).router
    request = _make_request("POST", "/foo", router=router)

    # Sanity: confirm the underlying matcher does report PARTIAL.
    match, _ = route.matches(request.scope)
    assert match == Match.PARTIAL

    assert _route_template(request) == "/foo"


def test_route_template_returns_unmatched_when_scope_lacks_router() -> None:
    request = _make_request("GET", "/anything", router=None)

    assert _route_template(request) == "_unmatched"


# ── PrometheusMiddleware ──────────────────────────────────────────────────


def _http_count(method: str, path: str, status: str) -> float:
    value: float = metrics.HTTP_REQUESTS.labels(
        method=method, path=path, status=status
    )._value.get()
    return value


def _hist_count(method: str, path: str) -> float:
    """Read the histogram ``*_count`` sample for one labelset."""
    target = {"method": method, "path": path}
    for m in metrics.HTTP_REQUEST_DURATION.collect():
        for s in m.samples:
            if s.name.endswith("_count") and s.labels == target:
                return s.value
    return 0.0


def _inflight(method: str) -> float:
    value: float = metrics.HTTP_REQUESTS_INFLIGHT.labels(method=method)._value.get()
    return value


def _build_app(*, raises: bool = False) -> Starlette:
    async def boom(_req: Request) -> PlainTextResponse:
        raise RuntimeError("kaboom")

    handler = boom if raises else _ok
    app = Starlette(routes=[Route("/x", handler, methods=["GET"])])
    app.add_middleware(PrometheusMiddleware)
    return app


async def test_prometheus_middleware_5xx_path_keeps_inflight_balanced() -> None:
    """When ``call_next`` raises, the middleware's finally clause must:

    * decrement the inflight gauge to its starting value,
    * observe the duration histogram exactly once,
    * tick ``http_requests_total`` with ``status="5xx"``.

    The ``path`` label is the route template (``/x``) — even on the
    exception path, because Starlette's Router populates
    ``scope["router"]`` inside its ``__call__`` *before* dispatching to
    the handler. So by the time control returns to PrometheusMiddleware's
    ``finally`` block (response or exception), the route is resolvable.
    """
    app = _build_app(raises=True)
    path_label = "/x"

    counter_before = _http_count("GET", path_label, "5xx")
    hist_before = _hist_count("GET", path_label)
    inflight_before = _inflight("GET")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        # Starlette's ServerErrorMiddleware converts the unhandled exception
        # into a 500 response — but that conversion happens *outside* our
        # middleware (ServerErrorMiddleware is added by Starlette as the
        # outermost wrapper), so PrometheusMiddleware sees the bare
        # exception and its ``status`` stays at the default "5xx".
        response = await client.get("/x")
        assert response.status_code == 500

    assert _inflight("GET") == inflight_before  # gauge balanced
    assert _hist_count("GET", path_label) - hist_before == 1
    assert _http_count("GET", path_label, "5xx") - counter_before == 1


async def test_prometheus_middleware_skips_metrics_path_entirely() -> None:
    """``/metrics`` is in EXCLUDED_PATHS — middleware short-circuits before
    touching the inflight gauge, the histogram, or the counter."""
    app = Starlette(routes=[Route("/metrics", _ok, methods=["GET"])])
    app.add_middleware(PrometheusMiddleware)

    counter_before = _http_count("GET", "/metrics", "2xx")
    hist_before = _hist_count("GET", "/metrics")
    inflight_before = _inflight("GET")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        r = await client.get("/metrics")
        assert r.status_code == 200

    # No deltas at all — the middleware never ran for this path.
    assert _http_count("GET", "/metrics", "2xx") == counter_before
    assert _hist_count("GET", "/metrics") == hist_before
    assert _inflight("GET") == inflight_before


def test_excluded_paths_set_contains_metrics() -> None:
    assert "/metrics" in PrometheusMiddleware.EXCLUDED_PATHS
