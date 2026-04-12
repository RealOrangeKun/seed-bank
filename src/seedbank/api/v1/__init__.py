"""v1 router aggregator. `main.py` imports `api_router` and mounts it once."""

from __future__ import annotations

from fastapi import APIRouter

from seedbank.core.config import get_settings

from . import api_keys, auth, users

api_router = APIRouter(prefix=get_settings().api_v1_prefix)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(api_keys.router)

__all__ = ["api_router"]
