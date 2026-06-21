"""Object-storage abstraction.

A `Protocol` rather than an ABC — alternate backends (e.g. fake in-memory for
tests, S3 in prod) just satisfy the interface.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Protocol


class ObjectStorage(Protocol):
    """Async object storage. All paths are `(bucket, key)` tuples."""

    async def ensure_bucket(self, bucket: str) -> None: ...

    async def put_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
    ) -> None: ...

    async def get_object(self, bucket: str, key: str) -> bytes: ...

    async def remove_object(self, bucket: str, key: str) -> None: ...

    async def object_exists(self, bucket: str, key: str) -> bool: ...

    async def presigned_put_url(
        self, bucket: str, key: str, ttl: timedelta, content_type: str | None = None
    ) -> str: ...

    async def presigned_get_url(self, bucket: str, key: str, ttl: timedelta) -> str: ...
