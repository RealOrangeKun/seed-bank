"""FastAPI application factory.

Stays small: mount middleware, mount routers, register exception handlers,
expose `/healthz`, `/readyz`, `/metrics`. Business logic lives in services.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware

from seedbank.api.errors import install_error_handlers
from seedbank.api.middleware import PrometheusMiddleware, RequestIdMiddleware
from seedbank.api.rate_limit import install_rate_limiter
from seedbank.api.v1 import api_router as api_v1_router
from seedbank.core.config import Settings, get_settings
from seedbank.core.logging import configure_logging, get_logger
from seedbank.core.metrics import metrics_response
from seedbank.core.sentry import init_sentry
from seedbank.core.tracing import init_tracing_for_api
from seedbank.infrastructure.analytics import close_clickhouse, get_clickhouse
from seedbank.infrastructure.cache import close_redis, get_redis
from seedbank.infrastructure.db.session import dispose_engine, get_sessionmaker
from seedbank.infrastructure.storage import bootstrap_buckets, get_storage

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    log.info("app.startup", env=settings.env, service=settings.service_name)
    # Eagerly construct singletons so cold-start cost lives outside the
    # request path, not inside the first /readyz check.
    get_sessionmaker()
    get_redis()
    get_storage()
    try:
        await bootstrap_buckets()
    except Exception as exc:
        log.warning("minio.bootstrap_failed", error=str(exc))
    yield
    log.info("app.shutdown")
    await dispose_engine()
    await close_redis()
    await close_clickhouse()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)
    # Sentry init before app creation so the SDK's request-context middleware
    # wraps our routes from the very first request.
    init_sentry(settings)

    app = FastAPI(
        title="Seed-Bank API",
        version="0.1.0",
        docs_url=f"{settings.api_v1_prefix}/docs",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = settings

    # Starlette ``add_middleware`` is LIFO: the **last** registered wraps
    # outermost. We want RequestId outermost so every log line — including
    # those from PrometheusMiddleware — carries a request_id, while
    # Prometheus measures handler-only time (excludes the negligible
    # RequestId overhead). Register Prometheus first, RequestId last.
    if settings.enable_metrics:
        app.add_middleware(PrometheusMiddleware)
    app.add_middleware(RequestIdMiddleware)
    if settings.cors_allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    # SessionMiddleware is required by authlib's OAuth flow to round-trip the
    # `state` parameter across the redirect to the provider.
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.jwt_secret.get_secret_value(),
        same_site="lax",
        https_only=settings.env == "prod",
    )

    install_error_handlers(app)
    install_rate_limiter(app)
    app.include_router(api_v1_router)

    # OTel must instrument FastAPI **after** routers are included; the
    # instrumentor walks the route table once and would miss anything
    # added later. No-op when ``OTEL_EXPORTER_OTLP_ENDPOINT`` is unset.
    # The /metrics, /healthz, /readyz endpoints below are excluded from
    # tracing via ``excluded_urls`` inside ``init_tracing_for_api`` — order
    # of registration relative to those routes is therefore not load-bearing.
    init_tracing_for_api(app, settings)

    if settings.enable_metrics:

        @app.get("/metrics", tags=["health"], include_in_schema=False)
        async def metrics() -> object:
            return metrics_response()

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz", tags=["health"])
    async def readyz() -> dict[str, object]:
        """Probes DB, Redis, MinIO, and ClickHouse. Returns degraded statuses
        per-component so the operator can tell what's broken from one ping.

        Production-model readiness is added in Phase 5 once the model
        manager exists.
        """
        checks: dict[str, str] = {}

        # DB
        try:
            sm = get_sessionmaker()
            async with sm() as session:
                await session.execute(text("SELECT 1"))
            checks["postgres"] = "ok"
        except Exception as exc:
            checks["postgres"] = f"down: {exc}"

        # Redis
        try:
            await get_redis().ping()
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"down: {exc}"

        # MinIO
        try:
            await get_storage().ensure_bucket(settings.minio_bucket_images)
            checks["minio"] = "ok"
        except Exception as exc:
            checks["minio"] = f"down: {exc}"

        # ClickHouse — non-blocking; analytics endpoints can degrade.
        try:
            ch = await get_clickhouse()
            checks["clickhouse"] = "ok" if await ch.ping() else "down"
        except Exception as exc:
            checks["clickhouse"] = f"down: {exc}"

        ok = all(v == "ok" for k, v in checks.items() if k != "clickhouse")
        return {"status": "ok" if ok else "degraded", "checks": checks}

    return app


app = create_app()


def cli() -> None:  # pragma: no cover
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "seedbank.main:app",
        host="0.0.0.0",  # noqa: S104
        port=8000,
        reload=settings.env == "dev",
        log_config=None,
    )
