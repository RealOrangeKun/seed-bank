"""OAuth provider clients.

`get_oauth()` returns the process-wide `authlib` `OAuth` registry with both
providers registered (when their credentials are present in `Settings`).
"""

from __future__ import annotations

from functools import lru_cache

from authlib.integrations.starlette_client import OAuth

from seedbank.core.config import Settings, get_settings

from . import github, google

__all__ = ["get_oauth", "github", "google"]


@lru_cache(maxsize=1)
def get_oauth(settings: Settings | None = None) -> OAuth:
    s = settings or get_settings()
    oauth = OAuth()
    google.register(oauth, s)
    github.register(oauth, s)
    return oauth
