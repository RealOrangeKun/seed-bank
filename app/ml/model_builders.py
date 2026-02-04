"""Model architecture builders for quality classification models."""
import torch
import torch.nn as nn
import torchvision.models as models
from app.ml.cbam import CBAM


def get_coffee_quality_model_v3():
    """
    Build ResNet18 coffee quality model with CBAM and hybrid pooling.
    
    Architecture:
    - ResNet18 backbone (ImageNet pretrained)
    - CBAM attention module after layer4
    - Hybrid pooling: GAP + GMP (concatenated)
    - Output: 1024 -> 1 (BCEWithLogitsLoss)
    
    Returns:
        PyTorch model ready for loading weights
    """
    model = models.resnet18(weights='IMAGENET1K_V1')
    
    # Add CBAM module
    model.cbam = CBAM(channels=512, reduction=16)
    
    # Replace FC layer for hybrid pooling output (512*2 = 1024)
    model.fc = nn.Linear(1024, 1)
    
    def forward_impl(x):
        """Custom forward pass with CBAM and hybrid pooling."""
        # Standard ResNet18 feature extraction
        x = model.conv1(x)
        x = model.bn1(x)
        x = model.relu(x)
        x = model.maxpool(x)
        
        x = model.layer1(x)
        x = model.layer2(x)
        x = model.layer3(x)
        x = model.layer4(x)
        
        # Apply CBAM attention
        x = model.cbam(x)
        
        # Hybrid pooling: concatenate GAP and GMP
        avg_pool = nn.AdaptiveAvgPool2d(1)(x)
        max_pool = nn.AdaptiveMaxPool2d(1)(x)
        x = torch.cat([avg_pool, max_pool], dim=1)
        
        # Flatten and classify
        x = torch.flatten(x, 1)
        return model.fc(x)
    
    # Replace forward method
    model.forward = forward_impl
    return model


def get_maize_quality_model_v4():
    """
    Build ResNet18 maize quality model with CBAM, hybrid pooling, and stride modification.
    
    Architecture:
    - ResNet18 backbone (ImageNet pretrained)
    - Modified stride in layer4 (1,1 instead of 2,2) for finer features
    - CBAM attention module after layer4
    - Hybrid pooling: GAP + GMP (concatenated)
    - Output: 1024 -> 1 (BCEWithLogitsLoss)
    
    Returns:
        PyTorch model ready for loading weights
    """
    model = models.resnet18(weights='IMAGENET1K_V1')
    
    # Stride Modification: reduce downsampling in layer4
    model.layer4[0].conv1.stride = (1, 1)
    model.layer4[0].downsample[0].stride = (1, 1)
    
    # Add CBAM module
    model.cbam = CBAM(channels=512, reduction=16)
    
    # Replace FC layer for hybrid pooling output (512*2 = 1024)
    model.fc = nn.Linear(1024, 1)
    
    def forward_impl(x):
        """Custom forward pass with CBAM and hybrid pooling."""
        # Standard ResNet18 feature extraction
        x = model.conv1(x)
        x = model.bn1(x)
        x = model.relu(x)
        x = model.maxpool(x)
        
        x = model.layer1(x)
        x = model.layer2(x)
        x = model.layer3(x)
        x = model.layer4(x)  # Modified stride preserves more spatial information
        
        # Apply CBAM attention
        x = model.cbam(x)
        
        # Hybrid pooling: concatenate GAP and GMP
        avg_pool = nn.AdaptiveAvgPool2d(1)(x)
        max_pool = nn.AdaptiveMaxPool2d(1)(x)
        x = torch.cat([avg_pool, max_pool], dim=1)
        
        # Flatten and classify
        x = torch.flatten(x, 1)
        return model.fc(x)
    
    # Replace forward method
    model.forward = forward_impl
    return model


def get_combined_detection_model():
    """
    Build FasterRCNN detection model with 3 classes.
    
    Classes:
    - 0: background
    - 1: coffee
    - 2: maize
    
    Returns:
        FasterRCNN model ready for loading weights
    """
    import torchvision
    from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
    
    # Load FasterRCNN with ResNet50-FPN backbone
    model = torchvision.models.detection.fasterrcnn_resnet50_fpn(weights=None)
    
    # Get number of input features for the classifier
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    
    # Replace the pre-trained head with a new one (3 classes: background, coffee, maize)
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes=3)
    
    return model
