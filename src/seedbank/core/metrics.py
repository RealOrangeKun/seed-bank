"""Prometheus metrics — registry and the counters/histograms we expose.

Phase 9 (observability). One module owns every metric the service emits so
labels and bucket choices stay consistent. Importers grab the metric they
need; the HTTP middleware and the ``/metrics`` endpoint share the registry.

Design:

* **Custom registry, not the default.** Tests import ``celery_app`` which
  imports task modules at module load; if metrics lived on the default
  ``REGISTRY`` we'd hit ``ValueError: Duplicated timeseries`` on a second
  import (e.g. when a fixture rebuilds the app). A scoped
  :class:`CollectorRegistry` keeps a fresh registry per process without
  fighting the default global one.
* **No runtime reset.** The metric handles below are bound at import
  time and held by callers in other modules (``api/middleware.py``,
  ``workers/tasks/dwh.py``). Rebuilding them at test time would orphan
  those bindings, so we deliberately do *not* expose a reset hook —
  tests assert deltas, not absolute values, and that's enough.
* **Path label uses Starlette's route template** (``/api/v1/users/{id}``),
  never the raw URL. Otherwise per-UUID requests blow up cardinality and
  Prometheus melts. Unmatched paths collapse to ``"_unmatched"``.
* **Duration histogram buckets** chosen for an API that's mostly
  sub-100ms with the long tail being analyze-style endpoints (uploads,
  presigns) — not for ML inference, which we measure separately.

The module's public surface is the metric objects + :func:`metrics_response`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

if TYPE_CHECKING:
    from starlette.responses import Response


# ── Registry ────────────────────────────────────────────────────────────────

REGISTRY: CollectorRegistry = CollectorRegistry(auto_describe=True)


HTTP_REQUESTS: Counter
HTTP_REQUEST_DURATION: Histogram
HTTP_REQUESTS_INFLIGHT: Gauge

DWH_DISPATCH: Counter
DWH_TASK_DURATION: Histogram

INFERENCE_TOTAL: Counter
INFERENCE_DURATION: Histogram

EXPERIMENT_RUN: Counter
AUTH_LOGIN: Counter


def _build(registry: CollectorRegistry) -> None:
    """Populate the module-level metric handles against ``registry``.

    Called once at import time. Not re-callable: prometheus_client refuses
    to register a duplicate timeseries against the same registry, and
    callers in other modules cache the names by reference.
    """
    global HTTP_REQUESTS, HTTP_REQUEST_DURATION, HTTP_REQUESTS_INFLIGHT
    global DWH_DISPATCH, DWH_TASK_DURATION
    global INFERENCE_TOTAL, INFERENCE_DURATION
    global EXPERIMENT_RUN, AUTH_LOGIN

    HTTP_REQUESTS = Counter(
        "http_requests_total",
        "HTTP requests, labelled by route template, method, and status class.",
        labelnames=("method", "path", "status"),
        registry=registry,
    )
    HTTP_REQUEST_DURATION = Histogram(
        "http_request_duration_seconds",
        "HTTP request duration in seconds.",
        labelnames=("method", "path"),
        # Tuned for an API that's mostly hot in <100ms; analyze/uploads
        # justify the >1s tail.
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        registry=registry,
    )
    HTTP_REQUESTS_INFLIGHT = Gauge(
        "http_requests_inflight",
        "HTTP requests currently being processed.",
        # method-only: the route template isn't resolvable until *after*
        # the Router has run, but the gauge has to inc on the way in. A
        # raw-URL fallback would leak labelsets into the registry under
        # diverse traffic (gauges retain labelsets forever, even after
        # they decrement to 0). Method alone keeps the cardinality
        # bounded at <10 and the gauge still answers "how loaded am I".
        labelnames=("method",),
        registry=registry,
    )

    DWH_DISPATCH = Counter(
        "seedbank_dwh_dispatch_total",
        "OLTP→ClickHouse dispatch attempts (Finding #5).",
        labelnames=("task", "result"),  # result ∈ {ok, disabled, error}
        registry=registry,
    )
    DWH_TASK_DURATION = Histogram(
        "seedbank_dwh_task_duration_seconds",
        "Worker-side execution time of a DWH sync task.",
        labelnames=("task", "result"),  # result ∈ {ok, error, not_found}
        buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
        registry=registry,
    )

    INFERENCE_TOTAL = Counter(
        "seedbank_inference_total",
        "Model inferences executed.",
        labelnames=("kind", "backend", "status"),  # status ∈ {ok, error}
        registry=registry,
    )
    INFERENCE_DURATION = Histogram(
        "seedbank_inference_duration_seconds",
        "Per-image inference duration in seconds.",
        labelnames=("kind", "backend"),
        buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
        registry=registry,
    )

    EXPERIMENT_RUN = Counter(
        "seedbank_experiment_run_total",
        "Offline-eval experiment runs by terminal status.",
        labelnames=("status",),
        registry=registry,
    )
    AUTH_LOGIN = Counter(
        "seedbank_auth_login_total",
        "Login attempts.",
        labelnames=("result",),  # result ∈ {ok, invalid_credentials, blocked}
        registry=registry,
    )


# Build once at import time so production starts with a clean registry.
_build(REGISTRY)


# ── Helpers ─────────────────────────────────────────────────────────────────


def metrics_response() -> Response:
    """Render the registry in Prometheus text format.

    Returns a Starlette ``Response`` (avoids importing FastAPI here so this
    module stays framework-light).
    """
    from starlette.responses import Response

    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


__all__ = [
    "AUTH_LOGIN",
    "CONTENT_TYPE_LATEST",
    "DWH_DISPATCH",
    "DWH_TASK_DURATION",
    "EXPERIMENT_RUN",
    "HTTP_REQUESTS",
    "HTTP_REQUESTS_INFLIGHT",
    "HTTP_REQUEST_DURATION",
    "INFERENCE_DURATION",
    "INFERENCE_TOTAL",
    "REGISTRY",
    "generate_latest",
    "metrics_response",
]
