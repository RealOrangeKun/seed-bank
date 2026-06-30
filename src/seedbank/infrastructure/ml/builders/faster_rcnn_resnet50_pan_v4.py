"""Faster R-CNN ResNet50-FPN + PANet superclass detector — v4 (4-seed head).

Same architecture as v1 (ported in ``_faster_rcnn_resnet50_pan.py``) but with a
5-class head: index 0 is background and 1-4 are the seed classes the V4 weights
(``Resnet50FPN_PANet_CIoU_ROI_V4.pth``) were trained on — pepper, maize, coffee,
garlic (order taken from the artifact's archive name; confirm with the trainer).
The class id → catalog ``seed_types.code`` mapping lives in the model's
``config.class_map`` so the worker can route each crop to its specialist.

Builder files are append-only by convention — v1 (21-class superclass head) is
left untouched so its production row keeps loading correctly; this is a separate
key, not a mutation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from seedbank.infrastructure.ml.builders._faster_rcnn_resnet50_pan import (
    create_resnet50_fasterrcnn,
)
from seedbank.infrastructure.ml.registry import register_builder

if TYPE_CHECKING:  # pragma: no cover — torch is in the [inference] extra
    from torch import nn

# 4 seed classes + background. Matches the cls_score head shape (5, 1024) in
# Resnet50FPN_PANet_CIoU_ROI_V4.pth.
_NUM_CLASSES = 5


@register_builder("faster-rcnn-resnet50-pan-v4")
def build() -> nn.Module:
    """ResNet50-FPN + PANet Faster R-CNN, 5-class head (bg + 4 seeds)."""
    return create_resnet50_fasterrcnn(num_classes=_NUM_CLASSES)


__all__ = ["build"]
