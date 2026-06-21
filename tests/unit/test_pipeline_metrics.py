"""Unit tests for INFERENCE_TOTAL / INFERENCE_DURATION wiring.

The pipelines (``infrastructure/ml/pipeline/{detect,classify}.py``) are
thin: pick a backend and call it. The Phase-9 wiring adds a counter +
duration histogram around the backend call, with ``status="ok"`` on
clean return and ``status="error"`` on any exception (re-raised).

We use a stub backend rather than the real torch_local / Roboflow ones
— pipelines accept a ``dict[str, InferenceBackend]`` so this is the
narrowest possible surface to exercise.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from seedbank.core import metrics
from seedbank.infrastructure.ml.backends.base import (
    BoundingBox,
    Classification,
    ClassificationConfig,
    Detection,
    DetectionConfig,
)
from seedbank.infrastructure.ml.pipeline.classify import ClassifyPipeline
from seedbank.infrastructure.ml.pipeline.detect import DetectPipeline

pytestmark = pytest.mark.unit


# ── Stub backends ──────────────────────────────────────────────────────────


class _StubBackend:
    name = "stub"

    def __init__(
        self,
        *,
        detection: list[Detection] | None = None,
        classification: Classification | None = None,
        raise_on_detect: bool = False,
        raise_on_classify: bool = False,
    ) -> None:
        self._detection = detection or []
        self._classification = classification or Classification(label="good", confidence=0.9)
        self._raise_on_detect = raise_on_detect
        self._raise_on_classify = raise_on_classify

    async def detect(self, image: bytes, cfg: DetectionConfig) -> list[Detection]:
        if self._raise_on_detect:
            raise RuntimeError("detect blew up")
        return self._detection

    async def classify(self, crop: bytes, cfg: ClassificationConfig) -> Classification:
        if self._raise_on_classify:
            raise RuntimeError("classify blew up")
        return self._classification


def _det_cfg() -> DetectionConfig:
    return DetectionConfig(
        model_id=uuid4(),
        artifact_uri="s3://bucket/key.pth",
        builder_key="dummy",
    )


def _cls_cfg() -> ClassificationConfig:
    return ClassificationConfig(
        model_id=uuid4(),
        artifact_uri="s3://bucket/key.pth",
        builder_key="dummy",
    )


# ── Helpers ────────────────────────────────────────────────────────────────


def _inf_total(kind: str, backend: str, status: str) -> float:
    value: float = metrics.INFERENCE_TOTAL.labels(
        kind=kind, backend=backend, status=status
    )._value.get()
    return value


def _inf_dur_count(kind: str, backend: str) -> float:
    """Read the histogram's ``_count`` sample.

    Histogram label children don't expose ``_count`` as an attribute; it
    lives in the rendered samples. Filter for the ``*_count`` sample with
    the matching labelset.
    """
    target = {"kind": kind, "backend": backend}
    for m in metrics.INFERENCE_DURATION.collect():
        for s in m.samples:
            if s.name.endswith("_count") and s.labels == target:
                return s.value
    return 0.0


# ── DetectPipeline ─────────────────────────────────────────────────────────


async def test_detect_happy_path_records_ok_and_duration() -> None:
    backend = _StubBackend(
        detection=[
            Detection(
                bbox=BoundingBox(0.1, 0.1, 0.2, 0.2),
                class_id=0,
                class_name="seed",
                confidence=0.9,
            )
        ]
    )
    pipeline = DetectPipeline(backends={"stub": backend})

    counter_before = _inf_total("detection", "stub", "ok")
    duration_before = _inf_dur_count("detection", "stub")

    outcome = await pipeline.run(image=b"\x00", cfg=_det_cfg(), backend_name="stub")

    assert len(outcome.detections) == 1
    assert _inf_total("detection", "stub", "ok") - counter_before == 1
    assert _inf_dur_count("detection", "stub") - duration_before == 1


async def test_detect_error_path_records_error_and_reraises() -> None:
    backend = _StubBackend(raise_on_detect=True)
    pipeline = DetectPipeline(backends={"stub": backend})

    err_before = _inf_total("detection", "stub", "error")
    duration_before = _inf_dur_count("detection", "stub")

    with pytest.raises(RuntimeError, match="detect blew up"):
        await pipeline.run(image=b"\x00", cfg=_det_cfg(), backend_name="stub")

    assert _inf_total("detection", "stub", "error") - err_before == 1
    # Duration is still observed in the ``finally`` — operators want the
    # latency of failures too.
    assert _inf_dur_count("detection", "stub") - duration_before == 1


# ── ClassifyPipeline ───────────────────────────────────────────────────────


async def test_classify_happy_path_records_ok_and_duration() -> None:
    backend = _StubBackend(classification=Classification(label="good", confidence=0.95))
    pipeline = ClassifyPipeline(backends={"stub": backend})

    counter_before = _inf_total("classification", "stub", "ok")
    duration_before = _inf_dur_count("classification", "stub")

    outcome = await pipeline.run(crop=b"\x00", cfg=_cls_cfg(), backend_name="stub")

    assert outcome.classification.label == "good"
    assert _inf_total("classification", "stub", "ok") - counter_before == 1
    assert _inf_dur_count("classification", "stub") - duration_before == 1


async def test_classify_error_path_records_error_and_reraises() -> None:
    backend = _StubBackend(raise_on_classify=True)
    pipeline = ClassifyPipeline(backends={"stub": backend})

    err_before = _inf_total("classification", "stub", "error")
    duration_before = _inf_dur_count("classification", "stub")

    with pytest.raises(RuntimeError, match="classify blew up"):
        await pipeline.run(crop=b"\x00", cfg=_cls_cfg(), backend_name="stub")

    assert _inf_total("classification", "stub", "error") - err_before == 1
    assert _inf_dur_count("classification", "stub") - duration_before == 1
