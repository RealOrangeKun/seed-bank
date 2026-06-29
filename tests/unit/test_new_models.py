"""Unit tests for the new two-stage model wiring.

Covers the framework-light contracts that don't need a GPU or the weights:
the seed taxonomy's internal consistency, the registry exposing every new
builder key, and the multi-label → good/bad collapse used by the EfficientNet-B2
specialists. The architecture/weight-load checks live in the inference-only
verification script (run on a GPU box), not here.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from seedbank.infrastructure.ml.backends.base import ClassificationConfig
from seedbank.infrastructure.ml.backends.torch_local import (
    _is_healthy_class,
    _multilabel_classification,
)
from seedbank.infrastructure.ml.registry import list_builders
from seedbank.infrastructure.ml.seed_taxonomy import (
    CLASS_MAP,
    SPECIALISTS,
    SPECIALISTS_BY_CODE,
    SUPERCLASSES,
)

# torch is in the [inference] extra; these tests build logits tensors directly.
torch = pytest.importorskip("torch")


def _cfg(classes: tuple[str, ...], threshold: float = 0.5) -> ClassificationConfig:
    return ClassificationConfig(
        model_id=uuid4(),
        artifact_uri="s3://m/k",
        builder_key="efficientnet-b2-cbam-maize-v1",
        threshold=threshold,
        image_size=260,
        classes=classes,
        segment=True,
    )


# ── taxonomy ──────────────────────────────────────────────────────────────────


def test_taxonomy_shapes():
    assert len(SUPERCLASSES) == 20
    assert len(SPECIALISTS) == 10
    # CLASS_MAP keys are the detector indices 1..20.
    assert sorted(CLASS_MAP) == list(range(1, 21))


def test_every_specialist_code_is_a_superclass():
    codes = {sc.code for sc in SUPERCLASSES}
    for spec in SPECIALISTS:
        assert spec.code in codes
        assert SPECIALISTS_BY_CODE[spec.code] is spec
        # head width matches the class list length
        assert len(spec.classes) >= 2


# ── registry ──────────────────────────────────────────────────────────────────


def test_registry_exposes_new_builders():
    keys = set(list_builders())
    assert "faster-rcnn-resnet50-pan-v1" in keys
    for spec in SPECIALISTS:
        assert spec.builder_key in keys
    # Old builders were removed in the model replacement.
    assert "faster-rcnn-combined-v1" not in keys
    assert "resnet18-cbam-coffee-v3" not in keys
    assert "resnet18-cbam-maize-v4" not in keys


# ── multi-label collapse ──────────────────────────────────────────────────────


def test_healthy_marker_detection():
    assert _is_healthy_class("Healthy_MAIZE")
    assert _is_healthy_class("01_intact_SOYBEAN")
    assert _is_healthy_class("GOOD_GARLIC")
    assert not _is_healthy_class("BAD_GARLIC")
    assert not _is_healthy_class("Fungus_MAIZE")
    assert not _is_healthy_class("02_cercospora_SOYBEAN")


def test_multilabel_defect_fires_bad():
    classes = ("Healthy_MAIZE", "Fungus_MAIZE")
    # logits chosen so sigmoid(Healthy) low, sigmoid(Fungus) high.
    logits = torch.tensor([[-4.0, 4.0]])
    out = _multilabel_classification(logits, _cfg(classes))
    assert out.label == "bad"
    assert "Fungus_MAIZE" in out.defects
    assert 0.0 <= out.confidence <= 1.0


def test_multilabel_only_healthy_fires_good():
    classes = ("GOOD_GARLIC", "BAD_GARLIC")
    logits = torch.tensor([[5.0, -5.0]])
    out = _multilabel_classification(logits, _cfg(classes))
    assert out.label == "good"
    assert out.defects == ()
    assert out.confidence > 0.9


def test_multilabel_nothing_fires_is_good():
    classes = ("GOOD_GARLIC", "BAD_GARLIC")
    logits = torch.tensor([[-1.0, -1.0]])  # both below 0.5
    out = _multilabel_classification(logits, _cfg(classes))
    assert out.label == "good"
    assert out.defects == ()
