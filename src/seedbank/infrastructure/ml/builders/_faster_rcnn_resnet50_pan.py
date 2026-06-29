"""ResNet50-FPN + PANet-neck Faster R-CNN architecture — private helper.

Ported verbatim (inference-relevant parts only) from
``seed-bank-app/model/rcnn_model.py`` so the saved ``FasterRcnn_Finale_V1.pth``
state dict loads with matching parameter keys. The training-only pieces of the
original module (focal-loss monkey-patching, the module-level execution block)
are intentionally dropped — only the forward architecture is needed to serve.

Filename starts with an underscore so the registry's autodiscovery skips it;
the registered builder lives in ``faster_rcnn_resnet50_pan_v1.py``.

Imports torch/torchvision at module top — only ever imported by the inference
worker (the API process never touches ``builders``).
"""

from __future__ import annotations

from typing import Any

from torch import nn
from torchvision import models
from torchvision.models.detection import FasterRCNN
from torchvision.models.detection.rpn import AnchorGenerator
from torchvision.ops import MultiScaleRoIAlign
from torchvision.ops.feature_pyramid_network import (
    FeaturePyramidNetwork,
    LastLevelMaxPool,
)


class PANetNeck(nn.Module):  # type: ignore[misc]
    """Bottom-up path-aggregation neck on top of the FPN pyramid."""

    def __init__(self, in_channels: int = 256, dropout_p: float = 0.15) -> None:
        super().__init__()
        self.p3_conv = nn.Sequential(
            nn.Conv2d(in_channels, in_channels, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Dropout2d(p=dropout_p),
        )
        self.p2_conv = nn.Sequential(
            nn.Conv2d(in_channels, in_channels, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Dropout2d(p=dropout_p),
        )
        self.p1_conv = nn.Sequential(
            nn.Conv2d(in_channels, in_channels, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Dropout2d(p=dropout_p),
        )
        self.p4_conv = nn.Sequential(
            nn.Conv2d(in_channels, in_channels, 3, padding=1),
            nn.ReLU(inplace=True),
            nn.Dropout2d(p=dropout_p),
        )
        self.upsample = nn.Upsample(scale_factor=2, mode="nearest")

    def forward(self, feats: dict[str, Any]) -> dict[str, Any]:
        # feats: {"0": P2, "1": P3, "2": P4, "3": P5, "pool": P6}
        p2 = feats["0"]
        p3 = feats["1"]
        p4 = feats["2"]
        p5 = feats["3"]
        p6 = feats["pool"]

        p4_bu = self.p4_conv(p4 + self.upsample(p5))
        p3_bu = self.p3_conv(p3 + self.upsample(p4_bu))
        p2_bu = self.p2_conv(p2 + self.upsample(p3_bu))
        p5_bu = self.p4_conv(p5)
        p6_bu = p6

        return {"0": p2_bu, "1": p3_bu, "2": p4_bu, "3": p5_bu, "pool": p6_bu}


class ResNet50FPNBackbone(nn.Module):  # type: ignore[misc]
    """ResNet50 stem/layers → 5-level FPN → PANet neck."""

    def __init__(self, pretrained: bool = False) -> None:
        super().__init__()
        weights = models.ResNet50_Weights.IMAGENET1K_V1 if pretrained else None
        resnet = models.resnet50(weights=weights)

        self.stem = nn.Sequential(
            resnet.conv1,
            resnet.bn1,
            resnet.relu,
            resnet.maxpool,
        )
        self.layer1 = resnet.layer1  # C2 — 256
        self.layer2 = resnet.layer2  # C3 — 512
        self.layer3 = resnet.layer3  # C4 — 1024
        self.layer4 = resnet.layer4  # C5 — 2048

        in_channels_list = [256, 512, 1024, 2048]
        self.out_channels = 256

        self.fpn = FeaturePyramidNetwork(
            in_channels_list=in_channels_list,
            out_channels=self.out_channels,
            extra_blocks=LastLevelMaxPool(),
        )
        self.pan = PANetNeck(in_channels=self.out_channels)

    def forward(self, x: Any) -> Any:
        x = self.stem(x)
        c2 = self.layer1(x)
        c3 = self.layer2(c2)
        c4 = self.layer3(c3)
        c5 = self.layer4(c4)
        fpn_feats = self.fpn({"0": c2, "1": c3, "2": c4, "3": c5})
        return self.pan(fpn_feats)


def create_resnet50_fasterrcnn(num_classes: int) -> FasterRCNN:
    """Assemble the Faster R-CNN exactly as trained in the standalone app."""
    backbone = ResNet50FPNBackbone(pretrained=False)

    anchor_sizes = ((16,), (32,), (64,), (128,), (256,))
    aspect_ratios = ((0.5, 1.0, 1.5),) * len(anchor_sizes)
    rpn_anchor_generator = AnchorGenerator(anchor_sizes, aspect_ratios)

    roi_pooler = MultiScaleRoIAlign(
        featmap_names=["0", "1", "2", "3", "pool"],
        output_size=7,
        sampling_ratio=2,
    )

    return FasterRCNN(
        backbone,
        num_classes=num_classes,
        min_size=448,
        max_size=448,
        rpn_anchor_generator=rpn_anchor_generator,
        box_roi_pool=roi_pooler,
        rpn_post_nms_top_n_train=1000,
        rpn_post_nms_top_n_test=500,
    )


__all__ = ["PANetNeck", "ResNet50FPNBackbone", "create_resnet50_fasterrcnn"]
