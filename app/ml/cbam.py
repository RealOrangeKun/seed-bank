"""Convolutional Block Attention Module (CBAM) implementation."""
import torch
import torch.nn as nn


class CBAM(nn.Module):
    """
    Convolutional Block Attention Module.
    
    Applies both channel attention and spatial attention to feature maps.
    Includes residual connections to prevent signal degradation.
    
    Args:
        channels: Number of input channels
        reduction: Channel reduction ratio for bottleneck (default: 16)
    """
    def __init__(self, channels, reduction=16):
        super(CBAM, self).__init__()
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.max_pool = nn.AdaptiveMaxPool2d(1)
        
        # Channel attention: shared MLP
        self.fc = nn.Sequential(
            nn.Conv2d(channels, channels // reduction, 1, bias=False),
            nn.ReLU(inplace=True),
            nn.Conv2d(channels // reduction, channels, 1, bias=False)
        )
        
        # Spatial attention
        self.conv_spatial = nn.Conv2d(2, 1, kernel_size=7, padding=3, bias=False)
        self.sigmoid = nn.Sigmoid()

        # Initialize weights to prevent signal degradation
        # Initialize the last conv of FC to zero so it doesn't kill the signal initially
        nn.init.constant_(self.fc[2].weight, 0)
        nn.init.constant_(self.conv_spatial.weight, 0)

    def forward(self, x):
        """
        Forward pass with channel and spatial attention.
        
        Args:
            x: Input feature map [B, C, H, W]
            
        Returns:
            Attention-weighted feature map with residual connection
        """
        residual = x  # Keep the original signal
        
        # Channel Attention
        avg_out = self.fc(self.avg_pool(x))
        max_out = self.fc(self.max_pool(x))
        channel_att = self.sigmoid(avg_out + max_out)
        x = x * channel_att
        
        # Spatial Attention
        avg_s = torch.mean(x, dim=1, keepdim=True)
        max_s, _ = torch.max(x, dim=1, keepdim=True)
        spatial = self.sigmoid(self.conv_spatial(torch.cat([avg_s, max_s], dim=1)))
        
        # Apply spatial attention with residual connection
        return (x * spatial) + residual
