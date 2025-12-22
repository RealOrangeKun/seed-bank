from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import torch
import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
import torch.nn as nn
import torchvision.models as models
from torchvision.ops import nms
import cv2
import numpy as np
from PIL import Image
import albumentations as A
from albumentations.pytorch import ToTensorV2
from torchvision import transforms
import io
from typing import List, Dict
import os

app = FastAPI(title="Seed Quality Detection API", version="1.0.0")

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for models
detection_model = None
classification_model = None
device = None

# Configuration
DETECTION_CONF_THRESHOLD = 0.90
CLASSIFICATION_THRESHOLD = 0.9
NMS_THRESHOLD = 0.3
IMAGE_SIZE = 224

# Transforms
detection_transform = A.Compose(
    [
        A.Resize(224, 224),
        A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ToTensorV2(),
    ]
)

classification_transform = transforms.Compose(
    [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)


@app.on_event("startup")
async def load_models():
    """Load both models on startup"""
    global detection_model, classification_model, device

    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
    print(f"Using device: {device}")

    # Load Faster R-CNN detection model
    detection_model_path = "models/FasterRCNN_ResNet50_Final.pth"
    if not os.path.exists(detection_model_path):
        raise Exception(f"Detection model not found at {detection_model_path}")

    detection_model = torchvision.models.detection.fasterrcnn_resnet50_fpn(weights=None)
    num_ftrs = detection_model.roi_heads.box_predictor.cls_score.in_features
    detection_model.roi_heads.box_predictor = FastRCNNPredictor(num_ftrs, 2)
    detection_model.load_state_dict(
        torch.load(detection_model_path, map_location=device)
    )
    detection_model.to(device)
    detection_model.eval()
    print("✓ Detection model loaded successfully")

    # Load ResNet50 classification model
    classification_model_path = "models/ResNet50_maize_seeds_NEW.pth"
    if not os.path.exists(classification_model_path):
        raise Exception(
            f"Classification model not found at {classification_model_path}"
        )

    classification_model = models.resnet50(weights=None)
    num_ftrs = classification_model.fc.in_features
    classification_model.fc = nn.Sequential(nn.Linear(num_ftrs, 1), nn.Sigmoid())
    classification_model.load_state_dict(
        torch.load(classification_model_path, map_location=device)
    )
    classification_model.to(device)
    classification_model.eval()
    print("✓ Classification model loaded successfully")


def process_uploaded_image(file_bytes: bytes) -> np.ndarray:
    """Convert uploaded file to RGB numpy array"""
    nparr = np.frombuffer(file_bytes, np.uint8)
    bgr_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if bgr_img is None:
        raise ValueError("Failed to decode image")
    rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
    return rgb_img


def detect_seeds(rgb_img: np.ndarray) -> tuple:
    """Run object detection and return boxes with scores"""
    orig_h, orig_w, _ = rgb_img.shape

    # Prepare image for detection
    transformed = detection_transform(image=rgb_img)
    img_tensor = transformed["image"].unsqueeze(0).to(device)

    # Run detection
    with torch.no_grad():
        prediction = detection_model(img_tensor)[0]

    boxes = prediction["boxes"]
    scores = prediction["scores"]

    # Apply NMS
    keep = nms(boxes, scores, NMS_THRESHOLD)
    boxes = boxes[keep].cpu().numpy()
    scores = scores[keep].cpu().numpy()

    # Filter by confidence and scale to original dimensions
    detected_seeds = []
    for box, score in zip(boxes, scores):
        if score > DETECTION_CONF_THRESHOLD:
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

            detected_seeds.append(
                {
                    "box": (x1_orig, y1_orig, x2_orig, y2_orig),
                    "detection_confidence": float(score),
                }
            )

    return detected_seeds, (orig_h, orig_w)


def classify_seeds(rgb_img: np.ndarray, detected_seeds: List[Dict]) -> List[Dict]:
    """Classify each detected seed as Good or Bad"""
    classified_results = []

    for seed_data in detected_seeds:
        x1, y1, x2, y2 = seed_data["box"]

        # Crop the seed region
        seed_crop = rgb_img[y1:y2, x1:x2]

        # Skip invalid crops
        if seed_crop.size == 0:
            continue

        # Convert to PIL for torchvision transforms
        pil_crop = Image.fromarray(seed_crop)
        crop_tensor = classification_transform(pil_crop).unsqueeze(0).to(device)

        # Classify
        with torch.no_grad():
            output = classification_model(crop_tensor)
            prob = output[0].item()

        # Determine label (based on your notebook logic)
        label = "Bad" if prob > CLASSIFICATION_THRESHOLD else "Good"

        classified_results.append(
            {
                "box": seed_data["box"],
                "detection_confidence": seed_data["detection_confidence"],
                "classification_probability": float(prob),
                "quality": label,
            }
        )

    return classified_results


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "Seed Quality Detection API",
        "models_loaded": detection_model is not None
        and classification_model is not None,
        "device": str(device),
    }


@app.post("/api/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """
    Single image analysis endpoint (for backward compatibility)
    
    Returns:
    - bounding_boxes: List of detected seeds with coordinates and quality
    - statistics: Overall quality metrics
    - image_dimensions: Original image size for frontend scaling
    """
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Read and process image
        contents = await file.read()
        rgb_img = process_uploaded_image(contents)

        # Step 1: Detect seeds
        detected_seeds, (img_height, img_width) = detect_seeds(rgb_img)

        if len(detected_seeds) == 0:
            return JSONResponse(
                content={
                    "success": True,
                    "message": "No seeds detected in the image",
                    "total_seeds": 0,
                    "bounding_boxes": [],
                    "statistics": {
                        "good_seeds": 0,
                        "bad_seeds": 0,
                        "good_percentage": 0.0,
                        "bad_percentage": 0.0,
                    },
                    "image_dimensions": {"width": img_width, "height": img_height},
                }
            )

        # Step 2: Classify seeds
        classified_results = classify_seeds(rgb_img, detected_seeds)

        # Step 3: Calculate statistics
        good_count = sum(1 for s in classified_results if s["quality"] == "Good")
        bad_count = sum(1 for s in classified_results if s["quality"] == "Bad")
        total_count = len(classified_results)

        # Format bounding boxes for frontend
        bounding_boxes = []
        for idx, seed in enumerate(classified_results):
            x1, y1, x2, y2 = seed["box"]
            bounding_boxes.append(
                {
                    "id": idx,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "width": x2 - x1,
                    "height": y2 - y1,
                    "quality": seed["quality"],
                    "detection_confidence": round(seed["detection_confidence"], 4),
                    "classification_probability": round(
                        seed["classification_probability"], 4
                    ),
                    "color": (
                        "#FF0000" if seed["quality"] == "Bad" else "#00FF00"
                    ),  # Red or Green
                }
            )

        response_data = {
            "success": True,
            "total_seeds": total_count,
            "bounding_boxes": bounding_boxes,
            "statistics": {
                "good_seeds": good_count,
                "bad_seeds": bad_count,
                "good_percentage": (
                    round((good_count / total_count * 100), 2) if total_count > 0 else 0
                ),
                "bad_percentage": (
                    round((bad_count / total_count * 100), 2) if total_count > 0 else 0
                ),
            },
            "image_dimensions": {"width": img_width, "height": img_height},
            "thresholds": {
                "detection_confidence": DETECTION_CONF_THRESHOLD,
                "classification_threshold": CLASSIFICATION_THRESHOLD,
            },
        }

        return JSONResponse(content=response_data)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/analyze-batch")
async def analyze_batch(files: List[UploadFile] = File(...)):
    """
    Batch analysis endpoint: Upload multiple images and get combined results
    Similar to how the notebook processes a folder of images
    
    Returns:
    - results: Array of results for each image
    - overall_statistics: Aggregated statistics across all images
    - total_images: Number of images processed
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")
        
        # Validate all files are images
        for file in files:
            if not file.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail=f"File {file.filename} is not an image")
        
        print(f"Processing {len(files)} images in batch...")
        
        # Process each image
        all_results = []
        total_good = 0
        total_bad = 0
        total_seeds = 0
        
        for file_idx, file in enumerate(files):
            # Read and process image
            contents = await file.read()
            rgb_img = process_uploaded_image(contents)
            
            # Step 1: Detect seeds
            detected_seeds, (img_height, img_width) = detect_seeds(rgb_img)
            
            # Step 2: Classify seeds (if any detected)
            if len(detected_seeds) > 0:
                classified_results = classify_seeds(rgb_img, detected_seeds)
                
                # Calculate statistics for this image
                good_count = sum(1 for s in classified_results if s["quality"] == "Good")
                bad_count = sum(1 for s in classified_results if s["quality"] == "Bad")
                
                # Format bounding boxes
                bounding_boxes = []
                for idx, seed in enumerate(classified_results):
                    x1, y1, x2, y2 = seed["box"]
                    bounding_boxes.append({
                        "id": idx,
                        "x1": x1,
                        "y1": y1,
                        "x2": x2,
                        "y2": y2,
                        "width": x2 - x1,
                        "height": y2 - y1,
                        "quality": seed["quality"],
                        "detection_confidence": round(seed["detection_confidence"], 4),
                        "classification_probability": round(seed["classification_probability"], 4),
                        "color": "#FF0000" if seed["quality"] == "Bad" else "#00FF00"
                    })
                
                total_good += good_count
                total_bad += bad_count
                total_seeds += len(classified_results)
            else:
                bounding_boxes = []
                good_count = 0
                bad_count = 0
            
            # Store result for this image
            image_result = {
                "filename": file.filename,
                "image_index": file_idx,
                "total_seeds": len(bounding_boxes),
                "bounding_boxes": bounding_boxes,
                "statistics": {
                    "good_seeds": good_count,
                    "bad_seeds": bad_count,
                    "good_percentage": round((good_count / len(bounding_boxes) * 100), 2) if len(bounding_boxes) > 0 else 0,
                    "bad_percentage": round((bad_count / len(bounding_boxes) * 100), 2) if len(bounding_boxes) > 0 else 0
                },
                "image_dimensions": {
                    "width": img_width,
                    "height": img_height
                }
            }
            all_results.append(image_result)
        
        # Calculate overall statistics
        overall_good_pct = round((total_good / total_seeds * 100), 2) if total_seeds > 0 else 0
        overall_bad_pct = round((total_bad / total_seeds * 100), 2) if total_seeds > 0 else 0
        
        response_data = {
            "success": True,
            "total_images": len(files),
            "total_seeds_all_images": total_seeds,
            "overall_statistics": {
                "good_seeds": total_good,
                "bad_seeds": total_bad,
                "good_percentage": overall_good_pct,
                "bad_percentage": overall_bad_pct
            },
            "results": all_results,
            "thresholds": {
                "detection_confidence": DETECTION_CONF_THRESHOLD,
                "classification_threshold": CLASSIFICATION_THRESHOLD
            }
        }
        
        return JSONResponse(content=response_data)
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/api/config")
async def get_config():
    """Get current configuration parameters"""
    return {
        "detection_confidence_threshold": DETECTION_CONF_THRESHOLD,
        "classification_threshold": CLASSIFICATION_THRESHOLD,
        "nms_threshold": NMS_THRESHOLD,
        "image_size": IMAGE_SIZE,
        "device": str(device),
    }


# Roboflow Client (Using requests due to Python 3.13 incompatibility with inference-sdk)
import requests
import base64

ROBOFLOW_API_KEY = "vBZaHEYnhnXfg0StVnqV"
ROBOFLOW_MODEL_ID = "maize-gslkp-3pcv5/9"
ROBOFLOW_URL = (
    f"https://detect.roboflow.com/{ROBOFLOW_MODEL_ID}?api_key={ROBOFLOW_API_KEY}"
)


@app.post("/api/analyze/fast")
async def analyze_image_fast(file: UploadFile = File(...)):
    """
    Fast endpoint using Roboflow for detection + Local ResNet for classification
    """
    try:
        # Validate file type
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Read image
        contents = await file.read()
        rgb_img = process_uploaded_image(contents)
        orig_h, orig_w, _ = rgb_img.shape

        # Call Roboflow API
        # We can send the image as base64
        img_base64 = base64.b64encode(contents).decode("utf-8")

        response = requests.post(
            ROBOFLOW_URL,
            data=img_base64,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if response.status_code != 200:
            raise Exception(f"Roboflow API Error: {response.text}")

        result = response.json()

        # Parse Roboflow results
        # Expected format: {'predictions': [{'x': 472.0, 'y': 407.0, 'width': 74.0, 'height': 82.0, 'confidence': 0.9, 'class': 'maize'}]}

        detected_seeds = []
        if "predictions" in result:
            for pred in result["predictions"]:
                # Convert center-x, center-y to x1, y1, x2, y2
                w = pred["width"]
                h = pred["height"]
                x = pred["x"]
                y = pred["y"]

                x1 = int(x - w / 2)
                y1 = int(y - h / 2)
                x2 = int(x + w / 2)
                y2 = int(y + h / 2)

                # Clip
                x1 = max(0, min(x1, orig_w))
                y1 = max(0, min(y1, orig_h))
                x2 = max(0, min(x2, orig_w))
                y2 = max(0, min(y2, orig_h))

                detected_seeds.append(
                    {
                        "box": (x1, y1, x2, y2),
                        "detection_confidence": float(pred["confidence"]),
                    }
                )
        if len(detected_seeds) == 0:
            return JSONResponse(
                content={
                    "success": True,
                    "message": "No seeds detected (Fast Mode)",
                    "total_seeds": 0,
                    "bounding_boxes": [],
                    "statistics": {
                        "good_seeds": 0,
                        "bad_seeds": 0,
                        "good_percentage": 0.0,
                        "bad_percentage": 0.0,
                    },
                    "image_dimensions": {"width": orig_w, "height": orig_h},
                }
            )

        # Step 2: Classify seeds (Reuse local model for accuracy)
        classified_results = classify_seeds(rgb_img, detected_seeds)

        # Step 3: Calculate statistics (Reuse logic)
        good_count = sum(1 for s in classified_results if s["quality"] == "Good")
        bad_count = sum(1 for s in classified_results if s["quality"] == "Bad")
        total_count = len(classified_results)

        # Format bounding boxes
        bounding_boxes = []
        for idx, seed in enumerate(classified_results):
            x1, y1, x2, y2 = seed["box"]
            bounding_boxes.append(
                {
                    "id": idx,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "width": x2 - x1,
                    "height": y2 - y1,
                    "quality": seed["quality"],
                    "detection_confidence": round(seed["detection_confidence"], 4),
                    "classification_probability": round(
                        seed["classification_probability"], 4
                    ),
                    "color": "#FF0000" if seed["quality"] == "Bad" else "#00FF00",
                }
            )

        return JSONResponse(
            content={
                "success": True,
                "mode": "fast",
                "total_seeds": total_count,
                "bounding_boxes": bounding_boxes,
                "statistics": {
                    "good_seeds": good_count,
                    "bad_seeds": bad_count,
                    "good_percentage": (
                        round((good_count / total_count * 100), 2)
                        if total_count > 0
                        else 0
                    ),
                    "bad_percentage": (
                        round((bad_count / total_count * 100), 2)
                        if total_count > 0
                        else 0
                    ),
                },
                "image_dimensions": {"width": orig_w, "height": orig_h},
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fast analysis failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
