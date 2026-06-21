"""Lightweight in-process rate limiting + upload guards (#16).

No external deps: a per-key sliding-window counter guarded by a lock. Suitable for a
single-process deployment; swap for Redis if horizontally scaled. Limits are configurable
via environment variables so tests/CI can tune or disable them.
"""
import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, UploadFile


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


# Config (env-overridable).
RATE_LIMIT_REQUESTS = _env_int("RATE_LIMIT_REQUESTS", 60)   # max requests per window
RATE_LIMIT_WINDOW_S = _env_int("RATE_LIMIT_WINDOW_S", 60)   # window length (seconds)
MAX_UPLOAD_MB = _env_int("MAX_UPLOAD_MB", 10)               # per-file size cap
MAX_BATCH_IMAGES = _env_int("MAX_BATCH_IMAGES", 20)         # max images per batch call
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024


class SlidingWindowRateLimiter:
    """Thread-safe per-key sliding-window limiter."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> tuple[bool, int]:
        """Record a hit for `key`. Returns (allowed, retry_after_seconds)."""
        if self.max_requests <= 0:  # disabled
            return True, 0
        now = time.monotonic()
        cutoff = now - self.window
        with self._lock:
            q = self._hits[key]
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= self.max_requests:
                retry_after = int(self.window - (now - q[0])) + 1
                return False, max(retry_after, 1)
            q.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


# Shared limiter for analyze endpoints.
analyze_limiter = SlidingWindowRateLimiter(RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW_S)


def enforce_rate_limit(key: str, limiter: SlidingWindowRateLimiter = analyze_limiter) -> None:
    """Raise 429 with Retry-After if `key` exceeds the limiter."""
    allowed, retry_after = limiter.check(key)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please slow down.",
            headers={"Retry-After": str(retry_after)},
        )


def guard_upload_size(contents: bytes, filename: str = "") -> None:
    """Raise 413 if a single uploaded file exceeds MAX_UPLOAD_BYTES."""
    if MAX_UPLOAD_BYTES and len(contents) > MAX_UPLOAD_BYTES:
        name = f" '{filename}'" if filename else ""
        raise HTTPException(
            status_code=413,
            detail=f"File{name} exceeds the {MAX_UPLOAD_MB} MB upload limit.",
        )


def guard_batch_count(files: list[UploadFile]) -> None:
    """Raise 400 if a batch exceeds MAX_BATCH_IMAGES."""
    if MAX_BATCH_IMAGES and len(files) > MAX_BATCH_IMAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many images: max {MAX_BATCH_IMAGES} per batch (got {len(files)}).",
        )
