"""Tiny detector fixture — pipeline smoke tests only.

A deliberately small, **untrained** Faster R-CNN (MobileNetV3-Large 320 FPN
backbone, 3-class head ``[background, coffee, maize]``) used to exercise the
real inference pipeline end-to-end in CI without shipping production weights.

This is the seed-bank analogue of HuggingFace's ``tiny-random-*`` fixtures:
the architecture and the code path are real, the weights are random. It
exists so the ``smoke`` workflow can prove the whole plumbing runs — worker
image, MinIO weight-fetch, ``load_state_dict``, detect/postprocess, persistence,
ClickHouse sync — *not* to produce meaningful detections. Never promote a
model built from this key in a real deployment.

torch + torchvision live in the ``[inference]`` extra; importing this module
from the API process will fail. That is by design — only the inference worker
should ever load this builder.
"""

from __future__ import annotations

import torchvision
from torch import nn
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor

from seedbank.infrastructure.ml.registry import register_builder


@register_builder("tiny-detector-smoke-v1")
def build() -> nn.Module:
    """MobileNetV3-320 Faster R-CNN, 3-class head, no pretrained weights.

    ``weights=None`` *and* ``weights_backbone=None`` keep construction fully
    offline — no ``torch.hub`` download — so a CI smoke run stays hermetic and
    fast. The random init is overwritten by the fixture's serialized state dict
    at load time; ``ModelManager`` loads ``strict=False`` regardless.
    """
    model = torchvision.models.detection.fasterrcnn_mobilenet_v3_large_320_fpn(
        weights=None,
        weights_backbone=None,
    )
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    # Classes: 0 = background, 1 = coffee, 2 = maize (mirrors faster-rcnn-combined-v1).
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes=3)
    return model


__all__ = ["build"]
