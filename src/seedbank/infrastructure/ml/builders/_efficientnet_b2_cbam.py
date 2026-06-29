"""EfficientNet-B2 + CBAM seed-quality classifier — private architecture helper.

Ported verbatim (module structure + attribute names) from
``seed-bank-app/model/efficient_net_B2_model.py::SeedQualityClassifier`` so the
trained specialist checkpoints (``checkpoints_<seed>/best_*.pt``) load with
matching parameter keys. This CBAM uses ``channel_attention``/``spatial_attention``
submodules, which differ from the ResNet builders' ``_cbam.CBAM`` — keep them
separate so neither's state_dict keys drift.

The head is a single ``Linear`` over concatenated GAP||GMP features producing
one logit per defect class; training used ``BCEWithLogitsLoss`` (multi-label).

timm lives in the ``[inference]`` extra; this module is only ever imported by
the inference worker.
"""

from __future__ import annotations

import timm
import torch
from torch import nn


class ChannelAttention(nn.Module):
    def __init__(self, channels: int, reduction: int = 16) -> None:
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        hidden = max(channels // reduction, 1)
        self.mlp = nn.Sequential(
            nn.Conv2d(channels, hidden, kernel_size=1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(hidden, channels, kernel_size=1, bias=False),
        )
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        avg_out = self.mlp(self.avg_pool(x))
        max_out = self.mlp(self.max_pool(x))
        return self.sigmoid(avg_out + max_out)


class SpatialAttention(nn.Module):
    def __init__(self, kernel_size: int = 7) -> None:
        super().__init__()
        self.conv = nn.Conv2d(2, 1, kernel_size, padding=kernel_size // 2, bias=False)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        avg_out = torch.mean(x, dim=1, keepdim=True)
        max_out, _ = torch.max(x, dim=1, keepdim=True)
        out = torch.cat([avg_out, max_out], dim=1)
        return self.sigmoid(self.conv(out))


class CBAM(nn.Module):
    def __init__(self, channels: int, reduction: int = 16, kernel_size: int = 7) -> None:
        super().__init__()
        self.channel_attention = ChannelAttention(channels, reduction)
        self.spatial_attention = SpatialAttention(kernel_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        identity = x
        x = x * self.channel_attention(x)
        x = x * self.spatial_attention(x)
        return x + identity


class SeedQualityClassifier(nn.Module):
    """EfficientNet-B2 backbone → CBAM → GAP||GMP → linear multi-label head."""

    def __init__(
        self,
        num_classes: int,
        backbone_name: str = "efficientnet_b2",
        pretrained: bool = False,
        dropout: float = 0.0,
    ) -> None:
        super().__init__()
        self.backbone = timm.create_model(
            backbone_name, pretrained=pretrained, num_classes=0, global_pool=""
        )
        self.num_features = self.backbone.num_features
        self.cbam = CBAM(self.num_features)
        self.gap = nn.AdaptiveAvgPool2d(1)
        self.gmp = nn.AdaptiveMaxPool2d(1)
        self.head = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(self.num_features * 2, num_classes),
        )

    def forward_features(self, x: torch.Tensor) -> torch.Tensor:
        f = self.backbone.forward_features(x)
        return self.cbam(f)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        f = self.forward_features(x)
        a = self.gap(f).flatten(1)
        m = self.gmp(f).flatten(1)
        pooled = torch.cat([a, m], dim=1)
        return self.head(pooled)


__all__ = ["CBAM", "SeedQualityClassifier"]
