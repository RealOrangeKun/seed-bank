"""OpenTelemetry tracing bootstrap.

Phase 9. Wires a single ``TracerProvider`` with an OTLP span exporter, plus
the auto-instrumentations that cover every IO boundary the service crosses:
FastAPI requests, SQLAlchemy + asyncpg sessions, Redis, outbound httpx, and
Celery tasks. All are no-ops at runtime when ``OTEL_EXPORTER_OTLP_ENDPOINT``
is unset, so the dev stack stays free of orphan exporters trying to dial
``localhost:4317``.

We deliberately keep instrumentation **optional and idempotent**:

* :func:`init_tracing_for_api` is called from the FastAPI lifespan and is a
  no-op when the OTLP endpoint is unset or already initialised.
* :func:`init_tracing_for_celery` is called from the Celery
  ``worker_process_init`` signal so each forked worker gets its own
  provider (forking after init breaks the OTLP exporter's gRPC channel).
* Each instrumentor is wrapped in try/except — instrumenting is "best
  effort"; a failure should never crash the API or a worker.

The module imports OTel lazily so the dev path that doesn't enable
tracing pays zero import cost beyond this file's own bytecode.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from seedbank.core.logging import get_logger

if TYPE_CHECKING:
    from fastapi import FastAPI

    from seedbank.core.config import Settings

log = get_logger(__name__)

_INITIALISED = False


def _otel_enabled(settings: Settings) -> bool:
    return bool(settings.otel_exporter_otlp_endpoint)


def _install_provider(settings: Settings) -> None:
    """Install a ``TracerProvider`` with an OTLP span processor.

    Idempotent — second call is a no-op. The exporter uses gRPC by default;
    consumers point ``OTEL_EXPORTER_OTLP_ENDPOINT`` at a collector
    (Tempo, Jaeger, OTel Collector, etc.).
    """
    global _INITIALISED
    if _INITIALISED:
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create(
        {
            "service.name": settings.service_name,
            "service.version": "0.1.0",
            "deployment.environment": settings.env,
        }
    )
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _INITIALISED = True
    log.info(
        "otel.provider_installed",
        endpoint=settings.otel_exporter_otlp_endpoint,
        service=settings.service_name,
    )


def init_tracing_for_api(app: FastAPI, settings: Settings) -> None:
    """Install OTel for the FastAPI process. No-op when OTLP endpoint unset."""
    if not _otel_enabled(settings):
        return
    _install_provider(settings)
    _instrument_common()
    _try_instrument(
        "fastapi",
        lambda: _instrument_fastapi(app),
    )


def init_tracing_for_celery(settings: Settings) -> None:
    """Install OTel for a forked Celery worker.

    Must run inside the ``worker_process_init`` signal handler — installing
    before fork leaks the gRPC channel into every child and the exporter
    silently drops spans.
    """
    if not _otel_enabled(settings):
        return
    _install_provider(settings)
    _instrument_common()
    _try_instrument("celery", _instrument_celery)


# ── Per-library instrumentors ──────────────────────────────────────────────


def _instrument_common() -> None:
    """Instrumentations shared by API + workers: SQLA, asyncpg, redis, httpx."""
    _try_instrument("sqlalchemy", _instrument_sqlalchemy)
    _try_instrument("asyncpg", _instrument_asyncpg)
    _try_instrument("redis", _instrument_redis)
    _try_instrument("httpx", _instrument_httpx)


def _try_instrument(name: str, fn: object) -> None:
    try:
        fn()  # type: ignore[operator]
    except Exception as exc:  # noqa: BLE001 — instrumenting must never crash boot
        log.warning("otel.instrument_failed", instrument=name, error=repr(exc))


def _instrument_fastapi(app: FastAPI) -> None:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)  # type: ignore[no-untyped-call]


def _instrument_sqlalchemy() -> None:
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

    SQLAlchemyInstrumentor().instrument()  # type: ignore[no-untyped-call]


def _instrument_asyncpg() -> None:
    from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor

    AsyncPGInstrumentor().instrument()  # type: ignore[no-untyped-call]


def _instrument_redis() -> None:
    from opentelemetry.instrumentation.redis import RedisInstrumentor

    RedisInstrumentor().instrument()  # type: ignore[no-untyped-call]


def _instrument_httpx() -> None:
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    HTTPXClientInstrumentor().instrument()  # type: ignore[no-untyped-call]


def _instrument_celery() -> None:
    from opentelemetry.instrumentation.celery import CeleryInstrumentor

    CeleryInstrumentor().instrument()  # type: ignore[no-untyped-call]


__all__ = ["init_tracing_for_api", "init_tracing_for_celery"]
