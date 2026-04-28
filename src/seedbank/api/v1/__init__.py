"""v1 router aggregator. `main.py` imports `api_router` and mounts it once."""

from __future__ import annotations

from fastapi import APIRouter

from seedbank.core.config import get_settings

from . import (
    analyze,
    api_keys,
    auth,
    batches,
    datasets,
    experiments,
    models,
    traffic,
    users,
)

api_router = APIRouter(prefix=get_settings().api_v1_prefix)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(api_keys.router)
api_router.include_router(models.router)
api_router.include_router(traffic.router)
api_router.include_router(analyze.router)
api_router.include_router(batches.router)
api_router.include_router(datasets.router)
api_router.include_router(experiments.router)

__all__ = ["api_router"]
