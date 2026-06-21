"""MinIO-backed `ObjectStorage` implementation using `miniopy-async`.

Bytes never traverse the API process for user uploads — clients PUT directly
to a presigned URL. The server only reads/writes when bootstrapping models
or pulling small artifacts (e.g. report markdown).

`ensure_bucket` is idempotent and safe to call on every startup.
"""

from __future__ import annotations

import io
from datetime import timedelta
from functools import lru_cache

from miniopy_async import Minio
from miniopy_async.error import S3Error

from seedbank.core.config import Settings, get_settings
from seedbank.core.exceptions import ExternalServiceError
from seedbank.core.logging import get_logger

log = get_logger(__name__)


class MinioStorage:
    """Async object storage. Implements the `ObjectStorage` Protocol."""

    def __init__(self, client: Minio, presign_client: Minio | None = None) -> None:
        self._client = client
        # Presigned GET URLs are consumed by browsers, so they must be signed
        # for an externally reachable host (see ``minio_public_endpoint``).
        # Falls back to the in-cluster client when no public client is given
        # (e.g. tests that talk to MinIO over a single hostname).
        self._presign_client = presign_client or client

    @classmethod
    def from_settings(cls, settings: Settings) -> MinioStorage:
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key.get_secret_value(),
            secret_key=settings.minio_secret_key.get_secret_value(),
            secure=settings.minio_secure,
        )
        presign_client = Minio(
            settings.minio_public_endpoint,
            access_key=settings.minio_access_key.get_secret_value(),
            secret_key=settings.minio_secret_key.get_secret_value(),
            secure=settings.minio_public_secure,
        )
        return cls(client, presign_client)

    async def ensure_bucket(self, bucket: str) -> None:
        try:
            if not await self._client.bucket_exists(bucket):
                await self._client.make_bucket(bucket)
                log.info("minio.bucket_created", bucket=bucket)
        except S3Error as exc:
            raise ExternalServiceError(f"minio: ensure_bucket {bucket}: {exc}") from exc

    async def put_object(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        try:
            await self._client.put_object(
                bucket,
                key,
                io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
        except S3Error as exc:
            raise ExternalServiceError(f"minio: put {bucket}/{key}: {exc}") from exc

    async def get_object(self, bucket: str, key: str) -> bytes:
        # miniopy-async 1.21+ requires the caller to pass an aiohttp
        # ClientSession for `get_object` (it does not for `put_object` /
        # `bucket_exists` / `stat_object`, which manage their own session).
        # We open and close one per call so the storage instance stays
        # stateless — uploads in this codebase are infrequent enough that
        # a per-call session is fine.
        import aiohttp

        try:
            # Nested, not combined: the inner CM needs `session` from the outer.
            async with aiohttp.ClientSession() as session:  # noqa: SIM117
                async with await self._client.get_object(bucket, key, session) as resp:
                    data: bytes = await resp.read()
                    return data
        except S3Error as exc:
            raise ExternalServiceError(f"minio: get {bucket}/{key}: {exc}") from exc

    async def remove_object(self, bucket: str, key: str) -> None:
        try:
            await self._client.remove_object(bucket, key)
        except S3Error as exc:
            raise ExternalServiceError(f"minio: remove {bucket}/{key}: {exc}") from exc

    async def object_exists(self, bucket: str, key: str) -> bool:
        try:
            await self._client.stat_object(bucket, key)
            return True
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject"}:
                return False
            raise ExternalServiceError(f"minio: stat {bucket}/{key}: {exc}") from exc

    async def presigned_put_url(
        self,
        bucket: str,
        key: str,
        ttl: timedelta,
        content_type: str | None = None,  # noqa: ARG002
    ) -> str:
        # `content_type` is enforced by the client headers when uploading; the
        # presign just authorizes the operation.
        url: str = await self._client.presigned_put_object(bucket, key, expires=ttl)
        return url

    async def presigned_get_url(self, bucket: str, key: str, ttl: timedelta) -> str:
        # Signed against the public endpoint so the resulting URL is reachable
        # from a browser, not just from inside the compose network.
        try:
            url: str = await self._presign_client.presigned_get_object(bucket, key, expires=ttl)
            return url
        except S3Error as exc:
            raise ExternalServiceError(f"minio: presign get {bucket}/{key}: {exc}") from exc


@lru_cache(maxsize=1)
def get_storage() -> MinioStorage:
    return MinioStorage.from_settings(get_settings())


async def bootstrap_buckets() -> None:
    """Create every bucket the app uses if missing. Safe to call on startup."""
    settings = get_settings()
    storage = get_storage()
    for bucket in (
        settings.minio_bucket_images,
        settings.minio_bucket_models,
        settings.minio_bucket_experiments,
        settings.minio_bucket_datasets,
    ):
        await storage.ensure_bucket(bucket)
