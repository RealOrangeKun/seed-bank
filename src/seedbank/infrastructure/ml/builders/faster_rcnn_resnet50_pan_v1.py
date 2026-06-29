"""Faster R-CNN ResNet50-FPN + PANet superclass detector — v1.

Stage-1 of the two-stage pipeline ported from the standalone desktop app
(``FasterRcnn_Finale_V1.pth``). The head emits 21 classes: index 0 is
background and 1-20 are the seed *superclasses* (SOYBEAN, MAIZE, GARLIC, …),
mapped to catalog seed types via the model's ``config.class_map``. A detected
crop is then routed to its EfficientNet-B2 specialist for fine-grained
defect classification.

Builder files are append-only by convention — never mutate a builder that a
``production`` model_artifacts row references; copy to a ``-v2`` key instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from seedbank.infrastructure.ml.builders._faster_rcnn_resnet50_pan import (
    create_resnet50_fasterrcnn,
)
from seedbank.infrastructure.ml.registry import register_builder

if TYPE_CHECKING:  # pragma: no cover — torch is in the [inference] extra
    from torch import nn

# 20 seed superclasses + background. Matches RCNN_NUM_CLASSES in the app config.
_NUM_CLASSES = 21


@register_builder("faster-rcnn-resnet50-pan-v1")
def build() -> nn.Module:
    """ResNet50-FPN + PANet Faster R-CNN, 21-class superclass head."""
    return create_resnet50_fasterrcnn(num_classes=_NUM_CLASSES)


__all__ = ["build"]
