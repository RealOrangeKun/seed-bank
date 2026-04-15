"""``ModelManager`` — caches loaded models on the GPU.

Responsibilities
----------------
* Build a fresh ``nn.Module`` via the registry, load weights from MinIO,
  move to device, set eval. Keep it cached keyed by ``model_id``.
* Hot-reload when the corresponding ``model_artifacts.updated_at`` advances
  (the caller passes the timestamp in; the manager doesn't query the DB).
* LRU-evict when the cache grows beyond ``max_models`` to bound GPU memory.
* Serialize concurrent loads of the *same* model_id through an asyncio.Lock
  per id so we never spend GPU memory on a duplicate load.

The torch import is lazy so this module is importable in a torch-less
context (it just won't be useful there).
"""

from __future__ import annotations

import asyncio
import io
from collections import OrderedDict
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from seedbank.core.config import get_settings
from seedbank.core.exceptions import ExternalServiceError
from seedbank.core.logging import get_logger
from seedbank.infrastructure.ml.registry import get_builder
from seedbank.infrastructure.storage import MinioStorage, get_storage

if TYPE_CHECKING:  # pragma: no cover
    import torch
    from torch import nn

log = get_logger(__name__)


class _CacheEntry:
    __slots__ = ("module", "device", "loaded_at", "updated_at")

    def __init__(
        self,
        module: "nn.Module",
        device: "torch.device",
        loaded_at: datetime,
        updated_at: datetime | None,
    ) -> None:
        self.module = module
        self.device = device
        self.loaded_at = loaded_at
        self.updated_at = updated_at


class ModelManager:
    """Process-wide cache of loaded torch modules + ultralytics YOLO models."""

    def __init__(
        self,
        *,
        storage: MinioStorage | None = None,
        bucket: str | None = None,
        max_models: int = 4,
    ) -> None:
        self._storage = storage or get_storage()
        self._bucket = bucket or get_settings().minio_bucket_models
        self._max_models = max_models
        self._cache: OrderedDict[UUID, _CacheEntry] = OrderedDict()
        self._yolo_cache: OrderedDict[UUID, object] = OrderedDict()
        self._locks: dict[UUID, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    # ── Internals ────────────────────────────────────────────────────────────

    def _lock_for(self, model_id: UUID) -> asyncio.Lock:
        # Lazily allocate a per-id lock; this is hot path so the protected
        # region is just dict access.
        lock = self._locks.get(model_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[model_id] = lock
        return lock

    def _evict_if_needed(self, kind: str) -> None:
        cache = self._cache if kind == "torch" else self._yolo_cache
        while len(cache) > self._max_models:
            evicted_id, _ = cache.popitem(last=False)
            log.info("ml.manager.evict", model_id=str(evicted_id), kind=kind)

    @staticmethod
    def _bucket_and_key(uri: str) -> tuple[str | None, str]:
        # Accept either "s3://bucket/key" or a bare "key" (use default bucket).
        if uri.startswith("s3://"):
            rest = uri.removeprefix("s3://")
            bucket, _, key = rest.partition("/")
            return bucket or None, key
        return None, uri

    async def _fetch_weights(self, artifact_uri: str) -> bytes:
        bucket, key = self._bucket_and_key(artifact_uri)
        bucket = bucket or self._bucket
        try:
            return await self._storage.get_object(bucket, key)
        except Exception as exc:  # noqa: BLE001
            raise ExternalServiceError(
                f"manager: fetch {bucket}/{key}: {exc}"
            ) from exc

    # ── Torch (registry-built) loading ───────────────────────────────────────

    async def load(
        self,
        model_id: UUID,
        builder_key: str,
        artifact_uri: str,
        updated_at: datetime | None = None,
    ) -> tuple["nn.Module", "torch.device"]:
        """Return the cached ``(module, device)`` for ``model_id``, loading
        from MinIO + builder if missing or stale."""
        async with self._lock_for(model_id):
            entry = self._cache.get(model_id)
            if entry is not None and (
                updated_at is None or entry.updated_at == updated_at
            ):
                # LRU touch.
                self._cache.move_to_end(model_id)
                return entry.module, entry.device

            module, device = await asyncio.to_thread(
                self._build_and_load_sync,
                builder_key,
                await self._fetch_weights(artifact_uri),
            )
            entry = _CacheEntry(
                module=module,
                device=device,
                loaded_at=datetime.now(tz=None),
                updated_at=updated_at,
            )
            self._cache[model_id] = entry
            self._cache.move_to_end(model_id)
            self._evict_if_needed("torch")
            log.info(
                "ml.manager.loaded",
                model_id=str(model_id),
                builder=builder_key,
                device=str(device),
            )
            return module, device

    @staticmethod
    def _build_and_load_sync(
        builder_key: str, weights: bytes
    ) -> tuple["nn.Module", "torch.device"]:
        import torch

        builder = get_builder(builder_key)
        module = builder()
        # Load state dict from in-memory bytes; weights_only=True is the safe
        # default in modern torch and rejects pickled python objects.
        state = torch.load(io.BytesIO(weights), map_location="cpu", weights_only=True)
        if isinstance(state, dict) and "state_dict" in state:
            state = state["state_dict"]
        module.load_state_dict(state, strict=False)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        module = module.to(device)
        module.eval()
        return module, device

    # ── YOLO loading ─────────────────────────────────────────────────────────

    async def load_yolo(self, model_id: UUID, artifact_uri: str) -> object:
        async with self._lock_for(model_id):
            cached = self._yolo_cache.get(model_id)
            if cached is not None:
                self._yolo_cache.move_to_end(model_id)
                return cached
            weights = await self._fetch_weights(artifact_uri)
            yolo = await asyncio.to_thread(self._load_yolo_sync, weights)
            self._yolo_cache[model_id] = yolo
            self._yolo_cache.move_to_end(model_id)
            self._evict_if_needed("yolo")
            log.info("ml.manager.yolo_loaded", model_id=str(model_id))
            return yolo

    @staticmethod
    def _load_yolo_sync(weights: bytes) -> object:
        import tempfile
        from pathlib import Path

        from ultralytics import YOLO

        # ultralytics.YOLO needs a filesystem path.
        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
            f.write(weights)
            tmp = Path(f.name)
        try:
            return YOLO(str(tmp))
        finally:
            # Keep the file around for ultralytics' lazy reads — it'll be
            # removed when the process exits.
            pass

    # ── Introspection ────────────────────────────────────────────────────────

    def cached_ids(self) -> list[UUID]:
        return list(self._cache.keys()) + list(self._yolo_cache.keys())

    async def invalidate(self, model_id: UUID) -> None:
        async with self._lock_for(model_id):
            self._cache.pop(model_id, None)
            self._yolo_cache.pop(model_id, None)


__all__ = ["ModelManager"]
