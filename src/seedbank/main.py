"""FastAPI application factory.

This file should stay small. Mount middleware, mount routers, register
exception handlers, expose `/healthz`, `/readyz`, `/metrics`. That's it.
Business logic does not live here.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from seedbank.core.config import Settings, get_settings
from seedbank.core.logging import configure_logging, get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown wiring.

    Future phases will plug DB engine, Redis pool, MinIO client, ClickHouse
    client, MLflow client, and ML model manager into ``app.state`` here.
    """
    settings: Settings = app.state.settings
    log.info("app.startup", env=settings.env, service=settings.service_name)
    yield
    log.info("app.shutdown")


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

    # Routers, middleware, error handlers, /metrics will be wired here in
    # later phases (auth, analyze, batches, models, experiments, …).

    @app.get("/healthz", tags=["health"])
    async def healthz() -> dict[str, str]:
        """Liveness — process is up."""
        return {"status": "ok"}

    @app.get("/readyz", tags=["health"])
    async def readyz() -> dict[str, str]:
        """Readiness — once dependencies are wired, this will probe DB / Redis /
        MinIO / ClickHouse and at least one production model."""
        return {"status": "ok"}

    return app


app = create_app()


def cli() -> None:  # pragma: no cover
    """Entry point exposed via ``[project.scripts]`` for `seedbank` command."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "seedbank.main:app",
        host="0.0.0.0",  # noqa: S104 — bind in container
        port=8000,
        reload=settings.env == "dev",
        log_config=None,  # we own logging via structlog
    )
