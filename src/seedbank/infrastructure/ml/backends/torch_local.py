"""Local torch inference backend.

Builds a fresh module via the registry, loads weights from MinIO, and runs
detect/classify on whatever device is available (CUDA preferred). Heavy
imports (torch, torchvision, PIL, numpy) live behind ``TYPE_CHECKING`` /
inside method bodies so importing this file in a torch-less context still
works (raising at runtime on first use).

The backend itself is **stateless** — model caching lives in
``ModelManager``; this class just runs forward passes on the module the
manager hands it.
"""

from __future__ import annotations

import asyncio
import io
from typing import TYPE_CHECKING

from seedbank.core.logging import get_logger
from seedbank.infrastructure.ml.backends.base import (
    BoundingBox,
    Classification,
    ClassificationConfig,
    Detection,
    DetectionConfig,
)

if TYPE_CHECKING:  # pragma: no cover
    import torch
    from torch import nn

log = get_logger(__name__)


_CLASS_NAMES = {0: "background", 1: "coffee", 2: "maize"}


class TorchLocalBackend:
    """Implements the ``InferenceBackend`` Protocol using local torch."""

    name = "torch_local"

    def __init__(self, manager: object | None = None) -> None:
        # The manager is injected lazily to avoid a circular import; we keep
        # it as a generic object since the protocol is duck-typed.
        self._manager = manager

    def bind_manager(self, manager: object) -> None:
        self._manager = manager

    # ── Detection ────────────────────────────────────────────────────────────

    async def detect(self, image: bytes, cfg: DetectionConfig) -> list[Detection]:
        if self._manager is None:
            raise RuntimeError("TorchLocalBackend requires a ModelManager.")
        module, device = await self._manager.load(  # type: ignore[attr-defined]
            cfg.model_id, cfg.builder_key, cfg.artifact_uri
        )
        return await asyncio.to_thread(self._detect_sync, module, device, image, cfg)

    @staticmethod
    def _detect_sync(
        module: nn.Module,
        device: torch.device,
        image: bytes,
        cfg: DetectionConfig,
    ) -> list[Detection]:
        import numpy as np
        import torch
        from PIL import Image

        img = Image.open(io.BytesIO(image)).convert("RGB")
        w, h = img.size
        arr = np.asarray(img, dtype=np.float32) / 255.0
        tensor = torch.from_numpy(arr).permute(2, 0, 1).to(device).contiguous()

        module.eval()
        with torch.no_grad():
            outputs = module([tensor])
        out = outputs[0]
        boxes = out["boxes"].detach().cpu().numpy()
        scores = out["scores"].detach().cpu().numpy()
        labels = out["labels"].detach().cpu().numpy()

        detections: list[Detection] = []
        for box, score, label in zip(boxes, scores, labels, strict=True):
            if score < cfg.confidence_threshold:
                continue
            x1, y1, x2, y2 = box.tolist()
            bw = max((x2 - x1) / w, 1e-6)
            bh = max((y2 - y1) / h, 1e-6)
            detections.append(
                Detection(
                    bbox=BoundingBox(
                        x=max(0.0, x1 / w),
                        y=max(0.0, y1 / h),
                        w=min(1.0, bw),
                        h=min(1.0, bh),
                    ),
                    class_id=int(label),
                    class_name=_CLASS_NAMES.get(int(label)),
                    confidence=float(score),
                )
            )
            if len(detections) >= cfg.max_detections:
                break
        return detections

    # ── Classification ───────────────────────────────────────────────────────

    async def classify(self, crop: bytes, cfg: ClassificationConfig) -> Classification:
        if self._manager is None:
            raise RuntimeError("TorchLocalBackend requires a ModelManager.")
        module, device = await self._manager.load(  # type: ignore[attr-defined]
            cfg.model_id, cfg.builder_key, cfg.artifact_uri
        )
        return await asyncio.to_thread(self._classify_sync, module, device, crop, cfg)

    @staticmethod
    def _classify_sync(
        module: nn.Module,
        device: torch.device,
        crop: bytes,
        cfg: ClassificationConfig,
    ) -> Classification:
        import torch
        from PIL import Image
        from torchvision import transforms

        img = Image.open(io.BytesIO(crop)).convert("RGB")
        tfm = transforms.Compose(
            [
                transforms.Resize((cfg.image_size, cfg.image_size)),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )
        tensor = tfm(img).unsqueeze(0).to(device)

        module.eval()
        with torch.no_grad():
            logits = module(tensor)
        score = float(torch.sigmoid(logits).squeeze().item())
        label = "good" if score >= cfg.threshold else "bad"
        confidence = score if label == "good" else 1.0 - score
        return Classification(label=label, confidence=confidence, raw_score=score)


__all__ = ["TorchLocalBackend"]
