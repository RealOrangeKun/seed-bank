"""Convolutional Block Attention Module (CBAM).

Ported as-is from ``legacy/app/ml/cbam.py``. Lives under ``builders/`` so it
sits next to the architectures that use it, but its filename starts with an
underscore so the registry's autodiscovery skips it.

This module only imports torch; do not import it from outside the
``infrastructure/ml/`` subtree.
"""

from __future__ import annotations

import torch
from torch import nn


class CBAM(nn.Module):
    """Channel + spatial attention with a residual signal."""

    def __init__(self, channels: int, reduction: int = 16) -> None:
        super().__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        self.fc = nn.Sequential(
            nn.Conv2d(channels, channels // reduction, 1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(channels // reduction, channels, 1, bias=False),
        )
        self.conv_spatial = nn.Conv2d(2, 1, kernel_size=7, padding=3, bias=False)
        self.sigmoid = nn.Sigmoid()
        # Initialize the last channel-FC conv and the spatial conv to zero so
        # the module starts as identity (residual only) — prevents signal
        # destruction on freshly-initialized weights.
        nn.init.constant_(self.fc[2].weight, 0)
        nn.init.constant_(self.conv_spatial.weight, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        avg_out = self.fc(self.avg_pool(x))
        max_out = self.fc(self.max_pool(x))
        channel_att = self.sigmoid(avg_out + max_out)
        x = x * channel_att

        avg_s = torch.mean(x, dim=1, keepdim=True)
        max_s, _ = torch.max(x, dim=1, keepdim=True)
        spatial = self.sigmoid(self.conv_spatial(torch.cat([avg_s, max_s], dim=1)))
        return (x * spatial) + residual


__all__ = ["CBAM"]
