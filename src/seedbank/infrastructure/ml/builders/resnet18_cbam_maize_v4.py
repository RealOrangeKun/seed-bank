"""ResNet18 + CBAM + hybrid-pool + stride-mod maize quality classifier — v4.

Ported from ``legacy/app/ml/model_builders.py::get_maize_quality_model_v4``.
Layer4 stride is reduced from 2 to 1 to preserve spatial resolution at the
attention stage. Output is a single logit (BCE).
"""

from __future__ import annotations

import torch
import torchvision.models as tvm
from torch import nn

from seedbank.infrastructure.ml.builders._cbam import CBAM
from seedbank.infrastructure.ml.registry import register_builder


@register_builder("resnet18-cbam-maize-v4")
def build() -> nn.Module:
    """ResNet18 with stride-1 layer4 + CBAM + hybrid pooling."""
    model = tvm.resnet18(weights="IMAGENET1K_V1")
    # Stride modification: keep more spatial info entering the attention block.
    model.layer4[0].conv1.stride = (1, 1)
    model.layer4[0].downsample[0].stride = (1, 1)

    model.cbam = CBAM(channels=512, reduction=16)
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

    model.forward = forward_impl  # type: ignore[assignment]
    return model


__all__ = ["build"]
