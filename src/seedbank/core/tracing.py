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

    # Skip health/metrics scrape endpoints — they would otherwise dominate
    # the trace volume with noise that has nothing to do with user traffic.
    FastAPIInstrumentor.instrument_app(  # type: ignore[no-untyped-call]
        app, excluded_urls="/metrics,/healthz,/readyz"
    )


def _instrument_sqlalchemy() -> None:
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

    # ``enable_commenter=False`` keeps SQL comments off the wire; SQLAlchemy
    # emits parameterised SQL by default (bind params live separately and are
    # not recorded as ``db.statement``), so PII via literal values is already
    # avoided. The instrumentor in 0.49b lacks a ``set_db_statement_to_query_only``
    # toggle for the SQLA dialect path.
    # TODO(security): revisit once opentelemetry-instrumentation-sqlalchemy
    # exposes a first-class statement-sanitisation flag.
    SQLAlchemyInstrumentor().instrument(  # type: ignore[no-untyped-call]
        enable_commenter=False,
    )


def _instrument_asyncpg() -> None:
    from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor

    # ``capture_parameters`` defaults to False in modern releases; we pass it
    # explicitly so a future default flip cannot silently leak bind values
    # (passwords, tokens, OAuth subjects) into spans.
    AsyncPGInstrumentor().instrument(  # type: ignore[no-untyped-call]
        capture_parameters=False,
    )


def _instrument_redis() -> None:
    from opentelemetry.instrumentation.redis import RedisInstrumentor

    # ``sanitize_query=True`` redacts the values of Redis command arguments
    # (token hashes, session payloads) while keeping the command name on
    # spans. Available since opentelemetry-instrumentation-redis 0.41.
    try:
        RedisInstrumentor().instrument(  # type: ignore[no-untyped-call]
            sanitize_query=True,
        )
    except TypeError:
        # TODO(security): instrumented version <0.41 lacks ``sanitize_query``
        # — sanitization deferred to upgrade.
        RedisInstrumentor().instrument()  # type: ignore[no-untyped-call]


def _instrument_httpx() -> None:
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    HTTPXClientInstrumentor().instrument(  # type: ignore[no-untyped-call]
        request_hook=_httpx_request_hook,
        response_hook=_httpx_response_hook,
    )


# ── HTTPX URL sanitisation ─────────────────────────────────────────────────
#
# MinIO presigned URLs and OAuth provider redirects carry secrets in the
# query string (``Signature``, ``X-Amz-*``, ``api_key``, ``token``). Strip
# them before they land on a span attribute.

_SENSITIVE_QUERY_KEYS: frozenset[str] = frozenset(
    {
        "signature",
        "api_key",
        "token",
        "access_token",
        "refresh_token",
        "code",
    }
)


def _scrub_url(url: str) -> str:
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    parts = urlsplit(url)
    if not parts.query:
        return url
    cleaned: list[tuple[str, str]] = []
    for k, v in parse_qsl(parts.query, keep_blank_values=True):
        lk = k.lower()
        if lk in _SENSITIVE_QUERY_KEYS or lk.startswith("x-amz-"):
            cleaned.append((k, "REDACTED"))
        else:
            cleaned.append((k, v))
    return urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(cleaned), parts.fragment)
    )


def _scrub_span_url_attributes(span: object) -> None:
    # ``span`` is a ReadableSpan-ish handle; ``set_attribute`` exists on the
    # mutable Span type the hooks receive. Guarded with getattr so a future
    # API change downgrades gracefully.
    set_attr = getattr(span, "set_attribute", None)
    get_attrs = getattr(span, "attributes", None)
    if set_attr is None or get_attrs is None:
        return
    for key in ("http.url", "http.target"):
        val = get_attrs.get(key) if hasattr(get_attrs, "get") else None
        if isinstance(val, str):
            set_attr(key, _scrub_url(val))


def _httpx_request_hook(span: object, request: object) -> None:  # noqa: ARG001
    _scrub_span_url_attributes(span)


def _httpx_response_hook(
    span: object, request: object, response: object
) -> None:  # noqa: ARG001
    _scrub_span_url_attributes(span)


def _instrument_celery() -> None:
    from opentelemetry.instrumentation.celery import CeleryInstrumentor

    CeleryInstrumentor().instrument()  # type: ignore[no-untyped-call]


__all__ = ["init_tracing_for_api", "init_tracing_for_celery"]
