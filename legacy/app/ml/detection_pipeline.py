"""
Updated detection and classification functions for multi-seed support.
This file contains the new implementations that need to be integrated into main.py.
"""
import torch
import numpy as np
from torchvision.ops import nms
from PIL import Image
from typing import List, Dict


def detect_seeds_multi(rgb_img: np.ndarray, model_manager, device, detection_transform, NMS_THRESHOLD, IMAGE_SIZE) -> tuple:
    """
    Run object detection with 3-class output (background, coffee, maize).
    
    Args:
        rgb_img: RGB image as numpy array
        model_manager: ModelManager instance
        device: PyTorch device
        detection_transform: Albumentations transform
        NMS_THRESHOLD: NMS threshold
        IMAGE_SIZE: Image size for scaling
        
    Returns:
        Tuple of (detected_seeds, (img_height, img_width))
        Each detected seed includes: box, detection_confidence, seed_type_id, seed_type_name
    """
    orig_h, orig_w, _ = rgb_img.shape

    # Prepare image for detection
    transformed = detection_transform(image=rgb_img)
    img_tensor = transformed["image"].unsqueeze(0).to(device)

    # Run detection with combined model (3 classes: background, coffee, maize)
    with torch.no_grad():
        prediction = model_manager.detection_model(img_tensor)[0]

    boxes = prediction["boxes"]
    scores = prediction["scores"]
    labels = prediction["labels"]  # 0=background, 1=coffee, 2=maize

    # Apply NMS
    keep = nms(boxes, scores, NMS_THRESHOLD)
    boxes = boxes[keep].cpu().numpy()
    scores = scores[keep].cpu().numpy()
    labels = labels[keep].cpu().numpy()

    # Get detection threshold
    detection_threshold = model_manager.get_detection_threshold()

    # Filter by confidence and scale to original dimensions
    detected_seeds = []
    for box, score, label in zip(boxes, scores, labels):
        # Skip background class (label=0) and low confidence
        if label == 0 or score <= detection_threshold:
            continue
            
        # Convert class ID to seed type
        # label=1 -> coffee (seed_type_id=2)
        # label=2 -> maize (seed_type_id=1)
        if label == 1:
            seed_type_id = model_manager.get_seed_type_id("coffee")
            seed_type_name = "coffee"
        elif label == 2:
            seed_type_id = model_manager.get_seed_type_id("maize")
            seed_type_name = "maize"
        else:
            continue  # Unknown class
        
        x1, y1, x2, y2 = box
        # Scale from 224x224 back to original dimensions
        x1_orig = int(x1 * (orig_w / IMAGE_SIZE))
        y1_orig = int(y1 * (orig_h / IMAGE_SIZE))
        x2_orig = int(x2 * (orig_w / IMAGE_SIZE))
        y2_orig = int(y2 * (orig_h / IMAGE_SIZE))

        # Clip to image boundaries
        x1_orig = max(0, min(x1_orig, orig_w))
        y1_orig = max(0, min(y1_orig, orig_h))
        x2_orig = max(0, min(x2_orig, orig_w))
        y2_orig = max(0, min(y2_orig, orig_h))

        detected_seeds.append({
            "box": (x1_orig, y1_orig, x2_orig, y2_orig),
            "detection_confidence": float(score),
            "seed_type_id": seed_type_id,
            "seed_type_name": seed_type_name,
        })

    return detected_seeds, (orig_h, orig_w)


def calculate_confidence_from_logits(logits: float, threshold: float) -> Dict:
    """
    Calculate confidence scores from BCEWithLogitsLoss output.
    
    Args:
        logits: Raw logits from model (can be any real number)
        threshold: Decision threshold (e.g., 0.0 for coffee, 5.0 for maize)
        
    Returns:
        Dictionary with confidence metrics
        
    Logic:
        - logits >= threshold -> Good quality
        - logits < threshold -> Bad quality
        - Higher logits indicate good seeds
        - Lower logits indicate bad seeds
    """
    # Determine quality
    is_good = logits >= threshold
    
    # Convert logits to probability-like scores for display
    # Using sigmoid for visualization (not for classification)
    from torch.nn.functional import sigmoid
    prob = sigmoid(torch.tensor(logits)).item()
    
    # For BCEWithLogitsLoss:
    # - Higher logits = more confident it's good
    # - Lower logits = more confident it's bad
    
    if is_good:
        # Distance from threshold (how much better than threshold)
        distance_from_threshold = abs(logits - threshold)
        confidence = min(100, (distance_from_threshold / (abs(threshold) + 1)) * 100)
        good_percentage = max(50, confidence)
        bad_percentage = 100 - good_percentage
    else:
        # Distance from threshold (how much worse than threshold)
        distance_from_threshold = abs(logits - threshold)
        confidence = min(100, (distance_from_threshold / (abs(threshold) + 1)) * 100)
        bad_percentage = max(50, confidence)
        good_percentage = 100 - bad_percentage
    
    return {
        "good_percentage": round(good_percentage, 2),
        "bad_percentage": round(bad_percentage, 2),
        "classification_confidence": round(prob * 100, 2),
        "raw_logits": round(logits, 4),
    }


def classify_seeds_multi(rgb_img: np.ndarray, detected_seeds: List[Dict], model_manager, device, classification_transform) -> List[Dict]:
    """
    Classify each detected seed using the appropriate quality model based on seed type.
    
    Args:
        rgb_img: RGB image as numpy array
        detected_seeds: List of detected seeds with seed_type_id
        model_manager: ModelManager instance
        device: PyTorch device
        classification_transform: torchvision transform
        
    Returns:
        List of classified seeds with quality labels and metrics
    """
    classified_results = []

    for seed_data in detected_seeds:
        x1, y1, x2, y2 = seed_data["box"]
        seed_type_id = seed_data["seed_type_id"]
        seed_type_name = seed_data["seed_type_name"]

        # Crop the seed region
        seed_crop = rgb_img[y1:y2, x1:x2]

        # Skip invalid crops
        if seed_crop.size == 0:
            continue

        # Calculate seed metrics
        width = x2 - x1
        height = y2 - y1
        area = width * height
        aspect_ratio = width / height if height > 0 else 1.0
        centroid_x = (x1 + x2) // 2
        centroid_y = (y1 + y2) // 2

        # Get appropriate quality model and threshold for this seed type
        quality_model, threshold = model_manager.get_quality_model(seed_type_id)

        # Convert to PIL for torchvision transforms
        pil_crop = Image.fromarray(seed_crop)
        crop_tensor = classification_transform(pil_crop).unsqueeze(0).to(device)

        # Classify (returns logits from BCEWithLogitsLoss)
        with torch.no_grad():
            logits = quality_model(crop_tensor)[0].item()

        # Determine label based on threshold
        # logits >= threshold = Good, logits < threshold = Bad
        label = "Good" if logits >= threshold else "Bad"

        # Calculate confidence scores
        confidence_metrics = calculate_confidence_from_logits(logits, threshold)

        classified_results.append({
            "box": seed_data["box"],
            "detection_confidence": seed_data["detection_confidence"],
            "seed_type_id": seed_type_id,
            "seed_type_name": seed_type_name,
            "quality": label,
            # Confidence metrics
            "good_percentage": confidence_metrics["good_percentage"],
            "bad_percentage": confidence_metrics["bad_percentage"],
            "classification_confidence": confidence_metrics["classification_confidence"],
            "raw_logits": confidence_metrics["raw_logits"],
            # Seed physical metrics
            "area": area,
            "width":width,
            "height": height,
            "aspect_ratio": round(aspect_ratio, 2),
            "centroid": {"x": centroid_x, "y": centroid_y},
        })

    return classified_results
