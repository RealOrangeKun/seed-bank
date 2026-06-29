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

from seedbank.core.config import get_settings
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

# Substrings that mark a specialist class as a *healthy* seed. Everything else
# (cercospora, fungus, broken, weeveled, …) is treated as a defect → "bad".
_HEALTHY_MARKERS = ("GOOD", "HEALTHY", "INTACT")


def _is_healthy_class(name: str) -> bool:
    upper = name.upper()
    if "BAD" in upper:
        return False
    return any(marker in upper for marker in _HEALTHY_MARKERS)


def _multilabel_classification(
    logits: torch.Tensor, cfg: ClassificationConfig
) -> Classification:
    """Collapse an EfficientNet-B2 specialist's per-class sigmoids into the
    platform's good/bad quality label while preserving the raw defect set.

    A crop is ``bad`` if any defect class crosses the threshold; if only healthy
    classes (or nothing) fire, it's ``good``. Confidence is the probability of
    the dominant class driving that decision.
    """
    import torch

    classes = cfg.classes or ()
    probs = torch.sigmoid(logits).detach().cpu().numpy().ravel().tolist()
    # Defensive: trust the shorter of (classes, probs) so a config/head mismatch
    # degrades gracefully instead of indexing past the end.
    n = min(len(classes), len(probs))
    fired = [
        (classes[i], probs[i])
        for i in range(n)
        if probs[i] >= cfg.threshold
    ]
    defects = tuple(name for name, _ in fired if not _is_healthy_class(name))

    if defects:
        # Bad: confidence = strongest defect signal.
        top = max((p for name, p in fired if not _is_healthy_class(name)), default=0.0)
        return Classification(
            label="bad", confidence=float(top), raw_score=float(top), defects=defects
        )

    # No defect crossed the threshold → good. Confidence = strongest healthy
    # signal, else 1 - strongest (uncertain) signal so it stays in [0, 1].
    healthy = [p for name, p in fired if _is_healthy_class(name)]
    conf = max(healthy) if healthy else 1.0 - (max(probs[:n]) if n else 0.0)
    return Classification(label="good", confidence=float(conf), raw_score=float(conf))


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
        return await asyncio.to_thread(
            self._detect_sync, module, device, image, cfg
        )

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
        # torchvision detectors (Faster R-CNN) run their own internal NMS using
        # ``roi_heads.nms_thresh`` (baked at construction, default 0.5) — the
        # ``iou_threshold`` in DetectionConfig is otherwise ignored on this path.
        # Drive it from the registered config so densely packed, overlapping seed
        # boxes get deduped. Guarded so a non-RCNN torch detector still works.
        roi_heads = getattr(module, "roi_heads", None)
        if roi_heads is not None and getattr(roi_heads, "nms_thresh", None) is not None:
            roi_heads.nms_thresh = float(cfg.iou_threshold)
        with torch.no_grad():
            outputs = module([tensor])
        out = outputs[0]
        boxes = out["boxes"].detach().cpu().numpy()
        scores = out["scores"].detach().cpu().numpy()
        labels = out["labels"].detach().cpu().numpy()

        # Prefer the per-model class map (superclass detector); fall back to the
        # legacy coffee/maize naming for the v1 combined detector.
        class_map = cfg.class_map or _CLASS_NAMES

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
                    class_name=class_map.get(int(label)),
                    confidence=float(score),
                )
            )
            if len(detections) >= cfg.max_detections:
                break
        return detections

    # ── Classification ───────────────────────────────────────────────────────

    async def classify(
        self, crop: bytes, cfg: ClassificationConfig
    ) -> Classification:
        if self._manager is None:
            raise RuntimeError("TorchLocalBackend requires a ModelManager.")
        module, device = await self._manager.load(  # type: ignore[attr-defined]
            cfg.model_id, cfg.builder_key, cfg.artifact_uri
        )
        return await asyncio.to_thread(
            self._classify_sync, module, device, crop, cfg
        )

    async def classify_batch(
        self, crops: list[bytes], cfg: ClassificationConfig
    ) -> list[Classification]:
        """Classify many crops that share one model in a single thread hop.

        The two-stage ("accurate") path produces one crop per detected seed —
        often hundreds per image. Running them one-at-a-time means hundreds of
        single-image forward passes (and event-loop thread hops). This batches
        them through the GPU/CPU in chunks instead, which is the dominant lever
        for that path's latency. Order is preserved: result[i] ↔ crops[i].
        """
        if not crops:
            return []
        if self._manager is None:
            raise RuntimeError("TorchLocalBackend requires a ModelManager.")
        module, device = await self._manager.load(  # type: ignore[attr-defined]
            cfg.model_id, cfg.builder_key, cfg.artifact_uri
        )
        return await asyncio.to_thread(
            self._classify_batch_sync, module, device, crops, cfg
        )

    @staticmethod
    def _preprocess_crop(
        crop: bytes, cfg: ClassificationConfig, tfm: object
    ) -> torch.Tensor:
        from PIL import Image

        img = Image.open(io.BytesIO(crop)).convert("RGB")
        # Optional U2NET background removal before the specialist sees the crop.
        # Honour both the per-model config and the global ops kill-switch, since
        # CPU matting per crop is the slow path operators may need to disable.
        if cfg.segment and get_settings().inference_segmentation_enabled:
            from seedbank.infrastructure.ml.segmentation import segment_crop

            img = segment_crop(img)
        return tfm(img)  # type: ignore[operator, no-any-return]

    @staticmethod
    def _make_transform(cfg: ClassificationConfig) -> object:
        from torchvision import transforms

        return transforms.Compose(
            [
                transforms.Resize((cfg.image_size, cfg.image_size)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
                ),
            ]
        )

    @staticmethod
    def _collapse_logits(row_logits: torch.Tensor, cfg: ClassificationConfig) -> Classification:
        import torch

        if cfg.classes:
            return _multilabel_classification(row_logits, cfg)
        # Legacy single-logit good/bad head.
        score = float(torch.sigmoid(row_logits).squeeze().item())
        label = "good" if score >= cfg.threshold else "bad"
        confidence = score if label == "good" else 1.0 - score
        return Classification(label=label, confidence=confidence, raw_score=score)

    @classmethod
    def _classify_sync(
        cls,
        module: nn.Module,
        device: torch.device,
        crop: bytes,
        cfg: ClassificationConfig,
    ) -> Classification:
        import torch

        tfm = cls._make_transform(cfg)
        tensor = cls._preprocess_crop(crop, cfg, tfm).unsqueeze(0).to(device)

        module.eval()
        with torch.no_grad():
            logits = module(tensor)
        return cls._collapse_logits(logits, cfg)

    @classmethod
    def _classify_batch_sync(
        cls,
        module: nn.Module,
        device: torch.device,
        crops: list[bytes],
        cfg: ClassificationConfig,
    ) -> list[Classification]:
        import torch

        tfm = cls._make_transform(cfg)
        chunk = max(1, get_settings().inference_classify_batch_size)
        module.eval()

        results: list[Classification] = []
        for start in range(0, len(crops), chunk):
            batch = crops[start : start + chunk]
            tensors = [cls._preprocess_crop(c, cfg, tfm) for c in batch]
            stacked = torch.stack(tensors).to(device)
            with torch.no_grad():
                logits = module(stacked)
            for i in range(logits.shape[0]):
                results.append(cls._collapse_logits(logits[i : i + 1], cfg))
        return results


__all__ = ["TorchLocalBackend"]
