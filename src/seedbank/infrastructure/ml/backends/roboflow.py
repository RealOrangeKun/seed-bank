"""Roboflow Hosted Inference backend.

Uses Roboflow's ``inference-sdk`` synchronous client wrapped in
``asyncio.to_thread`` (the SDK is sync). The API key is read from
``Settings.roboflow_api_key``; we never accept it from observed content.

Lives in the ``[inference]`` extra. The API process must not import this
file.
"""

from __future__ import annotations

import asyncio
import base64
from typing import TYPE_CHECKING

from seedbank.core.config import get_settings
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


class RoboflowBackend:
    """Calls Roboflow Hosted Inference via ``inference-sdk``.

    The Roboflow project slug + version are stored on the model_artifacts row
    as ``artifact_uri`` of the form ``roboflow://<workspace>/<project>/<version>``.
    """

    name = "roboflow"

    def __init__(self, api_url: str = "https://detect.roboflow.com") -> None:
        self._api_url = api_url
        self._client_lock = asyncio.Lock()
        self._client: object | None = None

    async def _get_client(self) -> object:
        if self._client is not None:
            return self._client
        async with self._client_lock:
            if self._client is not None:
                return self._client
            settings = get_settings()
            if settings.roboflow_api_key is None:
                raise ExternalServiceError("ROBOFLOW_API_KEY is not configured.")
            from inference_sdk import InferenceHTTPClient

            self._client = InferenceHTTPClient(
                api_url=self._api_url,
                api_key=settings.roboflow_api_key.get_secret_value(),
            )
            return self._client

    @staticmethod
    def _parse_uri(uri: str) -> str:
        # roboflow://workspace/project/version → "workspace/project/version"
        if uri.startswith("roboflow://"):
            return uri.removeprefix("roboflow://")
        return uri

    async def detect(self, image: bytes, cfg: DetectionConfig) -> list[Detection]:
        client = await self._get_client()
        model_id = self._parse_uri(cfg.artifact_uri)
        # The SDK accepts base64-encoded image bytes via the `inference_input`
        # field; we wrap the sync call in a thread.
        b64 = base64.b64encode(image).decode("ascii")
        try:
            result = await asyncio.to_thread(
                client.infer, b64, model_id=model_id  # type: ignore[attr-defined]
            )
        except Exception as exc:  # noqa: BLE001
            raise ExternalServiceError(f"roboflow infer failed: {exc}") from exc

        predictions = result.get("predictions", []) if isinstance(result, dict) else []
        img_w = float(result.get("image", {}).get("width", 1.0)) or 1.0
        img_h = float(result.get("image", {}).get("height", 1.0)) or 1.0

        detections: list[Detection] = []
        for pred in predictions:
            confidence = float(pred.get("confidence", 0.0))
            if confidence < cfg.confidence_threshold:
                continue
            x = float(pred.get("x", 0.0))
            y = float(pred.get("y", 0.0))
            w = float(pred.get("width", 0.0))
            h = float(pred.get("height", 0.0))
            detections.append(
                Detection(
                    bbox=BoundingBox(
                        x=max(0.0, (x - w / 2) / img_w),
                        y=max(0.0, (y - h / 2) / img_h),
                        w=min(1.0, w / img_w),
                        h=min(1.0, h / img_h),
                    ),
                    class_id=int(pred.get("class_id", 0)),
                    class_name=pred.get("class"),
                    confidence=confidence,
                )
            )
        return detections

    async def classify(
        self, crop: bytes, cfg: ClassificationConfig
    ) -> Classification:
        client = await self._get_client()
        model_id = self._parse_uri(cfg.artifact_uri)
        b64 = base64.b64encode(crop).decode("ascii")
        try:
            result = await asyncio.to_thread(
                client.infer, b64, model_id=model_id  # type: ignore[attr-defined]
            )
        except Exception as exc:  # noqa: BLE001
            raise ExternalServiceError(f"roboflow infer failed: {exc}") from exc

        # Single-label classifier output: top-1 prediction.
        if isinstance(result, dict) and "top" in result:
            label = str(result["top"])
            confidence = float(result.get("confidence", 0.0))
            return Classification(label=label, confidence=confidence)
        # Fallback: pick the first prediction.
        preds = result.get("predictions", {}) if isinstance(result, dict) else {}
        if isinstance(preds, dict) and preds:
            label = max(preds, key=lambda k: float(preds[k].get("confidence", 0.0)))
            return Classification(
                label=label, confidence=float(preds[label].get("confidence", 0.0))
            )
        raise ExternalServiceError("roboflow classify: empty response.")


__all__ = ["RoboflowBackend"]
