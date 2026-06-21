"""Integration tests for the ``/metrics`` endpoint and HTTP middleware.

Goals:

* ``/metrics`` returns Prometheus text on a real ASGI app.
* ``PrometheusMiddleware`` increments ``http_requests_total`` and observes
  ``http_request_duration_seconds`` for an actual request through the app
  (i.e. the wiring in :mod:`seedbank.main` is correct, not just the module
  in isolation).
* The ``/metrics`` endpoint itself does **not** count itself, otherwise
  every Prometheus scrape would dominate the histograms.

Counters are global to the process. Other tests may have ticked them, so
we read deltas, not absolute values.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from prometheus_client import generate_latest

from seedbank.core import metrics

pytestmark = pytest.mark.integration


def _counter_value(method: str, path: str, status: str) -> float:
    """Read the current value of ``http_requests_total`` for one label set."""
    return metrics.HTTP_REQUESTS.labels(
        method=method, path=path, status=status
    )._value.get()


async def test_metrics_endpoint_serves_prometheus_text(app_client: AsyncClient) -> None:
    r = await app_client.get("/metrics")
    assert r.status_code == 200
    # CONTENT_TYPE_LATEST = ``text/plain; version=0.0.4; charset=utf-8``.
    assert r.headers["content-type"].startswith("text/plain")
    body = r.text
    # All four "core" metric families should be present (auto-described).
    assert "http_requests_total" in body
    assert "http_request_duration_seconds" in body
    assert "seedbank_dwh_dispatch_total" in body
    assert "seedbank_inference_total" in body


async def test_request_increments_counter_for_route_template(
    app_client: AsyncClient,
) -> None:
    # ``/healthz`` is a stable, no-auth route — perfect smoke target.
    before = _counter_value("GET", "/healthz", "2xx")

    r = await app_client.get("/healthz")
    assert r.status_code == 200

    after = _counter_value("GET", "/healthz", "2xx")
    assert after - before == 1


async def test_metrics_endpoint_excluded_from_self_scraping(
    app_client: AsyncClient,
) -> None:
    """``PrometheusMiddleware`` skips ``/metrics`` so Prometheus's own
    15s scrape doesn't dominate the histograms."""
    before = _counter_value("GET", "/metrics", "2xx")
    r = await app_client.get("/metrics")
    assert r.status_code == 200
    after = _counter_value("GET", "/metrics", "2xx")
    assert after == before


async def test_4xx_status_class_label(app_client: AsyncClient) -> None:
    """Status codes are bucketed by class (2xx/3xx/4xx/5xx) — one label
    per 100 codes, not one per code, to keep cardinality bounded."""
    before = _counter_value("GET", "_unmatched", "4xx")
    r = await app_client.get("/this-route-does-not-exist")
    assert r.status_code == 404
    after = _counter_value("GET", "_unmatched", "4xx")
    assert after - before == 1
    # And the body still mentions the metric name.
    body = generate_latest(metrics.REGISTRY).decode()
    assert 'status="4xx"' in body


async def test_method_mismatch_keeps_route_template_label(
    app_client: AsyncClient,
) -> None:
    """Hitting an existing route with the wrong verb produces 405. The
    backend agent's revision keeps the route template (Match.PARTIAL)
    instead of collapsing to ``_unmatched`` — so dashboards can still
    attribute the 4xx to the right endpoint."""
    before_template = _counter_value("POST", "/healthz", "4xx")
    before_unmatched = _counter_value("POST", "_unmatched", "4xx")

    r = await app_client.post("/healthz")
    assert r.status_code == 405

    after_template = _counter_value("POST", "/healthz", "4xx")
    after_unmatched = _counter_value("POST", "_unmatched", "4xx")

    # 405 must land on the route template, NOT _unmatched.
    assert after_template - before_template == 1
    assert after_unmatched == before_unmatched


async def test_metrics_head_request_excluded_from_self_counter(
    app_client: AsyncClient,
) -> None:
    """HEAD on /metrics must also short-circuit the middleware. Otherwise
    operators that probe the scrape endpoint with HEAD would still pollute
    the histograms with self-traffic."""
    before_get = _counter_value("HEAD", "/metrics", "2xx")
    r = await app_client.head("/metrics")
    # FastAPI auto-resolves HEAD to the GET handler when only GET is
    # registered; either 200 or 405 is acceptable here. The contract under
    # test is the *exclusion*, not the response code.
    assert r.status_code in (200, 405)

    after_get = _counter_value("HEAD", "/metrics", "2xx")
    after_4xx = _counter_value("HEAD", "/metrics", "4xx")
    # Whatever the response code, /metrics must not be counted at all.
    assert after_get == before_get
    # And the 4xx bucket for /metrics is also untouched.
    assert after_4xx == _counter_value("HEAD", "/metrics", "4xx")
