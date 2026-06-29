"""ResNet18 + CBAM + hybrid-pool coffee quality classifier — v3.

Ported from ``legacy/app/ml/model_builders.py::get_coffee_quality_model_v3``.
Output is a single logit; training used ``BCEWithLogitsLoss``.

Builder files are append-only by convention. If the math changes, copy this
file to a new ``-v4`` filename and key — never silently mutate a builder
referenced by a ``production`` model_artifacts row.
"""

from __future__ import annotations

import torch
import torchvision.models as tvm
from torch import nn

from seedbank.infrastructure.ml.builders._cbam import CBAM
from seedbank.infrastructure.ml.registry import register_builder


@register_builder("resnet18-cbam-coffee-v3")
def build() -> nn.Module:
    """ResNet18 backbone + CBAM after layer4 + hybrid (GAP||GMP) pooling."""
    model = tvm.resnet18(weights="IMAGENET1K_V1")
    model.cbam = CBAM(channels=512, reduction=16)
    # Hybrid pooling concatenates GAP and GMP → 1024 features.
    model.fc = nn.Linear(1024, 1)

    def forward_impl(x: torch.Tensor) -> torch.Tensor:
        x = model.conv1(x)
        x = model.bn1(x)
        x = model.relu(x)
        x = model.maxpool(x)
        x = model.layer1(x)
        x = model.layer2(x)
        x = model.layer3(x)
        x = model.layer4(x)
        x = model.cbam(x)
        avg_pool = nn.AdaptiveAvgPool2d(1)(x)
        max_pool = nn.AdaptiveMaxPool2d(1)(x)
        x = torch.cat([avg_pool, max_pool], dim=1)
        x = torch.flatten(x, 1)
        return model.fc(x)

    model.forward = forward_impl
    return model


__all__ = ["build"]
