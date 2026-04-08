"""FastAPI application factory.

Stays small: mount middleware, mount routers, register exception handlers,
expose `/healthz`, `/readyz`, `/metrics`. Business logic lives in services.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from seedbank.api.errors import install_error_handlers
from seedbank.api.middleware import RequestIdMiddleware
from seedbank.core.config import Settings, get_settings
from seedbank.core.logging import configure_logging, get_logger
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
    except Exception as exc:  # noqa: BLE001
        log.warning("minio.bootstrap_failed", error=str(exc))
    yield
    log.info("app.shutdown")
    await dispose_engine()
    await close_redis()
    await close_clickhouse()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="Seed-Bank API",
        version="0.1.0",
        docs_url=f"{settings.api_v1_prefix}/docs",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = settings

    # Order matters: RequestId first so CORS/error-handler logs already have a request_id.
    app.add_middleware(RequestIdMiddleware)
    if settings.cors_allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allow_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    install_error_handlers(app)

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
        except Exception as exc:  # noqa: BLE001
            checks["postgres"] = f"down: {exc}"

        # Redis
        try:
            await get_redis().ping()
            checks["redis"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["redis"] = f"down: {exc}"

        # MinIO
        try:
            await get_storage().ensure_bucket(settings.minio_bucket_images)
            checks["minio"] = "ok"
        except Exception as exc:  # noqa: BLE001
            checks["minio"] = f"down: {exc}"

        # ClickHouse — non-blocking; analytics endpoints can degrade.
        try:
            ch = await get_clickhouse()
            checks["clickhouse"] = "ok" if await ch.ping() else "down"
        except Exception as exc:  # noqa: BLE001
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
