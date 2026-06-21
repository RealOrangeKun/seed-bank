"""Faster R-CNN combined coffee+maize detector — v1.

Ported from ``legacy/app/ml/model_builders.py::get_combined_detection_model``.
Three-class head: ``[background, coffee, maize]``.

torch + torchvision live in the ``[inference]`` extra; importing this module
from the API process will fail. That is by design — only the inference
worker should ever load this builder.
"""

from __future__ import annotations

import torchvision
from torch import nn  # required at builder-build time (runtime use, not just typing)
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

from seedbank.infrastructure.ml.registry import register_builder


@register_builder("faster-rcnn-combined-v1")
def build() -> nn.Module:
    """Faster R-CNN with ResNet50-FPN backbone, 3-class head."""
    model = torchvision.models.detection.fasterrcnn_resnet50_fpn(weights=None)
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    # Classes: 0 = background, 1 = coffee, 2 = maize.
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes=3)
    return model


__all__ = ["build"]
