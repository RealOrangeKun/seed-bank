"""Ultralytics YOLO backend.

Wraps ``ultralytics.YOLO`` for both detection and classification heads.
Like ``torch_local``, the heavy import lives behind ``TYPE_CHECKING`` so
this file stays importable in the API process (failing only on use).
"""

from __future__ import annotations

import asyncio
import io
from typing import TYPE_CHECKING

from seedbank.core.exceptions import ExternalServiceError
from seedbank.core.logging import get_logger
from seedbank.infrastructure.ml.backends.base import (
    BoundingBox,
    Classification,
    ClassificationConfig,
    Detection,
    DetectionConfig,
)

if TYPE_CHECKING:  # pragma: no cover
    pass

log = get_logger(__name__)


class UltralyticsYoloBackend:
    """Implements ``InferenceBackend`` via ``ultralytics.YOLO``.

    Like ``torch_local``, model loading is delegated to the ``ModelManager``
    so cache lifecycle and concurrency are uniform across backends.
    """

    name = "yolo"

    def __init__(self, manager: object | None = None) -> None:
        self._manager = manager

    def bind_manager(self, manager: object) -> None:
        self._manager = manager

    async def detect(self, image: bytes, cfg: DetectionConfig) -> list[Detection]:
        if self._manager is None:
            raise RuntimeError("UltralyticsYoloBackend requires a ModelManager.")
        yolo = await self._manager.load_yolo(  # type: ignore[attr-defined]
            cfg.model_id, cfg.artifact_uri
        )
        return await asyncio.to_thread(self._detect_sync, yolo, image, cfg)

    @staticmethod
    def _detect_sync(yolo: object, image: bytes, cfg: DetectionConfig) -> list[Detection]:
        from PIL import Image

        img = Image.open(io.BytesIO(image)).convert("RGB")
        w, h = img.size
        try:
            results = yolo.predict(  # type: ignore[attr-defined]
                source=img,
                conf=cfg.confidence_threshold,
                iou=cfg.iou_threshold,
                max_det=cfg.max_detections,
                imgsz=cfg.image_size or 640,
                verbose=False,
            )
        except Exception as exc:  # noqa: BLE001
            raise ExternalServiceError(f"yolo predict failed: {exc}") from exc

        detections: list[Detection] = []
        if not results:
            return detections
        result = results[0]
        names = getattr(result, "names", {}) or {}
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return detections
        xyxy = boxes.xyxy.detach().cpu().numpy()
        scores = boxes.conf.detach().cpu().numpy()
        labels = boxes.cls.detach().cpu().numpy().astype(int)

        for box, score, label in zip(xyxy, scores, labels, strict=True):
            x1, y1, x2, y2 = box.tolist()
            detections.append(
                Detection(
                    bbox=BoundingBox(
                        x=max(0.0, x1 / w),
                        y=max(0.0, y1 / h),
                        w=min(1.0, max((x2 - x1) / w, 1e-6)),
                        h=min(1.0, max((y2 - y1) / h, 1e-6)),
                    ),
                    class_id=int(label),
                    class_name=names.get(int(label)),
                    confidence=float(score),
                )
            )
        return detections

    async def classify(
        self, crop: bytes, cfg: ClassificationConfig
    ) -> Classification:
        if self._manager is None:
            raise RuntimeError("UltralyticsYoloBackend requires a ModelManager.")
        yolo = await self._manager.load_yolo(  # type: ignore[attr-defined]
            cfg.model_id, cfg.artifact_uri
        )
        return await asyncio.to_thread(self._classify_sync, yolo, crop, cfg)

    @staticmethod
    def _classify_sync(
        yolo: object, crop: bytes, cfg: ClassificationConfig
    ) -> Classification:
        from PIL import Image

        img = Image.open(io.BytesIO(crop)).convert("RGB")
        try:
            results = yolo.predict(  # type: ignore[attr-defined]
                source=img,
                imgsz=cfg.image_size,
                verbose=False,
            )
        except Exception as exc:  # noqa: BLE001
            raise ExternalServiceError(f"yolo classify failed: {exc}") from exc
        if not results:
            raise ExternalServiceError("yolo classify: empty results.")
        probs = getattr(results[0], "probs", None)
        names = getattr(results[0], "names", {}) or {}
        if probs is None:
            raise ExternalServiceError("yolo classify: no probs in result.")
        top1 = int(probs.top1)
        confidence = float(probs.top1conf)
        return Classification(
            label=str(names.get(top1, str(top1))), confidence=confidence
        )


__all__ = ["UltralyticsYoloBackend"]
