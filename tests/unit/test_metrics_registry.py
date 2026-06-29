"""Unit tests for the Prometheus registry wiring.

The point of these tests is the contract: every metric the rest of the
codebase imports exists, has the labelnames we promise, and lives in our
custom registry (so a second ``create_app()`` in the same process doesn't
trip ``Duplicated timeseries``).
"""

from __future__ import annotations

import pytest
from prometheus_client import CollectorRegistry

from seedbank.core import metrics

pytestmark = pytest.mark.unit


def test_registry_is_isolated_collector_registry() -> None:
    """Should be our own registry, not the default global one."""
    assert isinstance(metrics.REGISTRY, CollectorRegistry)
    # Default Prometheus registry exposes ``python_info`` automatically; ours
    # doesn't because we never registered platform collectors against it.
    body = metrics.generate_latest(metrics.REGISTRY).decode()
    assert "python_info" not in body


def test_http_counter_has_expected_labels() -> None:
    # ``in body`` substring assertion: registry is process-global, so we
    # don't assert the absolute count — only that the labelled timeseries
    # exists after we increment it. Other tests adding the same label set
    # would still leave this assertion green.
    metrics.HTTP_REQUESTS.labels(method="GET", path="/healthz", status="2xx").inc()
    body = metrics.generate_latest(metrics.REGISTRY).decode()
    assert 'http_requests_total{method="GET",path="/healthz",status="2xx"}' in body


def test_dwh_dispatch_counter_supports_finding_5() -> None:
    """Finding #5 demanded an alertable failure-rate counter on
    ``dispatch_after_commit``. The counter must label both task and result.

    Substring-presence is sufficient because the registry is process-global;
    delta-based tests live in ``test_dwh_helpers.py``.
    """
    metrics.DWH_DISPATCH.labels(task="seedbank.dwh.sync_inference", result="ok").inc()
    metrics.DWH_DISPATCH.labels(task="seedbank.dwh.sync_inference", result="error").inc()
    body = metrics.generate_latest(metrics.REGISTRY).decode()
    assert "seedbank_dwh_dispatch_total" in body
    assert 'result="ok"' in body
    assert 'result="error"' in body


# ── Label-shape contracts ──────────────────────────────────────────────────
#
# Every metric the rest of the codebase imports has a labelset that
# downstream call sites depend on. Pin the shape so a refactor that adds
# or drops a label fails here, not in production.


def _labels_of(metric: object) -> tuple[str, ...]:
    return tuple(metric._labelnames)  # type: ignore[attr-defined]


def test_inference_total_label_shape() -> None:
    assert _labels_of(metrics.INFERENCE_TOTAL) == ("kind", "backend", "status")


def test_inference_duration_label_shape() -> None:
    assert _labels_of(metrics.INFERENCE_DURATION) == ("kind", "backend")


def test_auth_login_label_shape() -> None:
    assert _labels_of(metrics.AUTH_LOGIN) == ("result",)


def test_experiment_run_label_shape() -> None:
    assert _labels_of(metrics.EXPERIMENT_RUN) == ("status",)


def test_http_request_duration_label_shape() -> None:
    assert _labels_of(metrics.HTTP_REQUEST_DURATION) == ("method", "path")


def test_dwh_task_duration_label_shape() -> None:
    assert _labels_of(metrics.DWH_TASK_DURATION) == ("task", "result")


def test_metrics_response_returns_prometheus_content_type() -> None:
    resp = metrics.metrics_response()
    assert resp.status_code == 200
    # CONTENT_TYPE_LATEST is the exposition-format header advertised by
    # prometheus_client; format and version vary by client version.
    assert resp.headers["content-type"] == metrics.CONTENT_TYPE_LATEST
    assert "text/plain" in resp.headers["content-type"]
