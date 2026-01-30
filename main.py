from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, Response, StreamingResponse
from typing import Optional
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
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

# Database imports
from app.database import get_db
from app.models import User, ScanBatch, ScanImage, SeedDetection, ProcessingStatus, QualityLabel
from app.crud import (
    get_or_create_guest_user, 
    generate_device_fingerprint,
    get_user_by_fingerprint,
    get_user_batches,
    get_batch_by_id_and_user,
    get_batch_detections,
    get_user_statistics
)

app = FastAPI(title="Bank Seed Demo API", version="1.0.0")

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


def save_image_to_storage(file_contents: bytes, batch_id: int, filename: str, image_index: int = 0) -> str:
    """
    Save uploaded image to local storage with MinIO-ready path structure.
    
    Args:
        file_contents: Image file bytes
        batch_id: Scan batch ID
        filename: Original filename (used for extension)
        image_index: Index of image in batch (0, 1, 2, ...) for unique filenames
        
    Returns:
        Storage path (relative, MinIO-ready format)
    """
    # Create batch directory
    batch_dir = f"uploads/batches/{batch_id}"
    os.makedirs(batch_dir, exist_ok=True)
    
    # Get file extension
    ext = os.path.splitext(filename)[1] or ".jpg"
    
    # Save image with unique name per index
    image_path = f"{batch_dir}/image_{image_index}{ext}"
    with open(image_path, "wb") as f:
        f.write(file_contents)
    
    # Return MinIO-ready path (relative, can be converted to s3:// later)
    return image_path


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


def calculate_confidence_score(
    prob: float, threshold: float = 0.9, k: float = 8.0
) -> Dict:
    """
    Calculate confidence scores based on distance from threshold with exponential weighting.

    Args:
        prob: Classification probability (0-1)
        threshold: Decision threshold (default 0.9)
        k: Exponential coefficient for amplifying differences (higher = stronger early differences)

    Returns:
        Dictionary with confidence metrics
    """
    # Calculate distance from threshold
    distance = abs(prob - threshold)

    # Exponential confidence: amplifies early differences
    # confidence ranges from 0 to ~100%
    # Using 1 - e^(-k * distance) formula
    confidence = prob

    confidence *= 100

    # Good percentage: inverse of probability (lower prob = more good)
    good_percentage = (1 - prob) * 100

    # Bad percentage: direct probability
    bad_percentage = prob * 100

    # Determine which side of threshold
    is_bad = prob > threshold

    return {
        "good_percentage": round(good_percentage, 2),
        "bad_percentage": round(bad_percentage, 2),
        "classification_confidence": round(
            confidence, 2
        ),  # How confident we are in the classification
        "raw_probability": round(prob, 4),  # Keep raw value for reference
    }


def classify_seeds(rgb_img: np.ndarray, detected_seeds: List[Dict]) -> List[Dict]:
    """Classify each detected seed as Good or Bad with detailed confidence metrics"""
    classified_results = []

    for seed_data in detected_seeds:
        x1, y1, x2, y2 = seed_data["box"]

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

        # Convert to PIL for torchvision transforms
        pil_crop = Image.fromarray(seed_crop)
        crop_tensor = classification_transform(pil_crop).unsqueeze(0).to(device)

        # Classify
        with torch.no_grad():
            output = classification_model(crop_tensor)
            prob = output[0].item()

        # Determine label (based on your notebook logic)
        label = "Bad" if prob > CLASSIFICATION_THRESHOLD else "Good"

        # Calculate confidence scores
        confidence_metrics = calculate_confidence_score(prob, CLASSIFICATION_THRESHOLD)

        classified_results.append(
            {
                "box": seed_data["box"],
                "detection_confidence": seed_data["detection_confidence"],
                "quality": label,
                # New detailed metrics
                "good_percentage": confidence_metrics["good_percentage"],
                "bad_percentage": confidence_metrics["bad_percentage"],
                "classification_confidence": confidence_metrics[
                    "classification_confidence"
                ],
                "raw_probability": confidence_metrics["raw_probability"],
                # Seed physical metrics
                "area": area,
                "width": width,
                "height": height,
                "aspect_ratio": round(aspect_ratio, 2),
                "centroid": {"x": centroid_x, "y": centroid_y},
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
async def analyze_image(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Single image analysis endpoint (for backward compatibility)

    Returns:
    - bounding_boxes: List of detected seeds with coordinates and quality
    - statistics: Overall quality metrics
    - image_dimensions: Original image size for frontend scaling
    """
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Extract device fingerprint from request headers
        user_agent = request.headers.get("user-agent", "")
        client_host = request.client.host if request.client else None
        device_fingerprint = generate_device_fingerprint(user_agent, client_host)

        # Get or create guest user (will reuse if fingerprint matches)
        guest_user = get_or_create_guest_user(db, device_fingerprint)
        
        # Create scan batch
        processing_start = datetime.utcnow()
        scan_batch = ScanBatch(
            user_id=guest_user.id,
            status=ProcessingStatus.PROCESSING,
            processing_start_at=processing_start
        )
        db.add(scan_batch)
        db.flush()
        
        # Read and process image
        contents = await file.read()
        rgb_img = process_uploaded_image(contents)

        # Step 1: Detect seeds
        detected_seeds, (img_height, img_width) = detect_seeds(rgb_img)

        if len(detected_seeds) == 0:
            # Save image even if no seeds detected
            storage_path = save_image_to_storage(contents, scan_batch.id, file.filename or "image.jpg")
            scan_image = ScanImage(
                batch_id=scan_batch.id,
                storage_path=storage_path,
                original_filename=file.filename,
                width=img_width,
                height=img_height
            )
            db.add(scan_image)
            
            # Update batch as completed with zero seeds
            processing_end = datetime.utcnow()
            scan_batch.status = ProcessingStatus.COMPLETED
            scan_batch.processing_end_at = processing_end
            scan_batch.processing_duration_ms = int((processing_end - processing_start).total_seconds() * 1000)
            db.commit()
            
            return JSONResponse(
                content={
                    "success": True,
                    "batch_id": scan_batch.id,
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
        
        # Save image to storage
        storage_path = save_image_to_storage(contents, scan_batch.id, file.filename or "image.jpg")
        
        # Create scan image record
        scan_image = ScanImage(
            batch_id=scan_batch.id,
            storage_path=storage_path,
            original_filename=file.filename,
            width=img_width,
            height=img_height
        )
        db.add(scan_image)
        db.flush()
        
        # Calculate average confidence
        avg_confidence = (
            sum(s["classification_confidence"] for s in classified_results) / total_count
            if total_count > 0 else 0.0
        )
        
        # Save seed detections
        for seed_data in classified_results:
            x1, y1, x2, y2 = seed_data["box"]
            
            # Normalize bounding box coordinates (0.0-1.0)
            box_x_norm = x1 / img_width if img_width > 0 else 0.0
            box_y_norm = y1 / img_height if img_height > 0 else 0.0
            box_w_norm = (x2 - x1) / img_width if img_width > 0 else 0.0
            box_h_norm = (y2 - y1) / img_height if img_height > 0 else 0.0
            
            detection = SeedDetection(
                batch_id=scan_batch.id,
                image_id=scan_image.id,
                quality_label=QualityLabel.GOOD if seed_data["quality"] == "Good" else QualityLabel.BAD,
                confidence_score=seed_data["classification_confidence"] / 100.0,  # Convert percentage to 0-1
                detection_confidence=seed_data["detection_confidence"],
                box_x_norm=box_x_norm,
                box_y_norm=box_y_norm,
                box_w_norm=box_w_norm,
                box_h_norm=box_h_norm,
                area=seed_data["area"],
                width=seed_data["width"],
                height=seed_data["height"],
                aspect_ratio=seed_data["aspect_ratio"],
                centroid_x=seed_data["centroid"]["x"],
                centroid_y=seed_data["centroid"]["y"],
                good_percentage=seed_data["good_percentage"],
                bad_percentage=seed_data["bad_percentage"]
            )
            db.add(detection)
        
        # Update batch with final statistics
        processing_end = datetime.utcnow()
        processing_duration_ms = int((processing_end - processing_start).total_seconds() * 1000)
        
        scan_batch.status = ProcessingStatus.COMPLETED
        scan_batch.total_seeds = total_count
        scan_batch.bad_seeds_count = bad_count
        scan_batch.avg_confidence_score = avg_confidence / 100.0  # Convert to 0-1
        scan_batch.processing_end_at = processing_end
        scan_batch.processing_duration_ms = processing_duration_ms
        
        # Commit all changes
        db.commit()

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
                    "width": seed["width"],
                    "height": seed["height"],
                    "area": seed["area"],
                    "aspect_ratio": seed["aspect_ratio"],
                    "centroid": seed["centroid"],
                    "quality": seed["quality"],
                    "detection_confidence": round(seed["detection_confidence"], 4),
                    "good_percentage": seed["good_percentage"],
                    "bad_percentage": seed["bad_percentage"],
                    "classification_confidence": seed["classification_confidence"],
                    "raw_probability": seed["raw_probability"],
                    "color": (
                        "#FF0000" if seed["quality"] == "Bad" else "#00FF00"
                    ),  # Red or Green
                }
            )

        response_data = {
            "success": True,
            "batch_id": scan_batch.id,
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
        if 'db' in locals():
            db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if 'db' in locals():
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/analyze-batch")
async def analyze_batch(
    request: Request,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
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
            if not file.content_type or not file.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=400, detail=f"File {file.filename} is not an image"
                )

        # Extract device fingerprint from request headers
        user_agent = request.headers.get("user-agent", "")
        client_host = request.client.host if request.client else None
        device_fingerprint = generate_device_fingerprint(user_agent, client_host)

        # Get or create guest user (will reuse if fingerprint matches)
        guest_user = get_or_create_guest_user(db, device_fingerprint)
        
        # Create scan batch for the entire batch
        processing_start = datetime.utcnow()
        scan_batch = ScanBatch(
            user_id=guest_user.id,
            status=ProcessingStatus.PROCESSING,
            processing_start_at=processing_start
        )
        db.add(scan_batch)
        db.flush()

        print(f"Processing {len(files)} images in batch...")

        # Process each image
        all_results = []
        total_good = 0
        total_bad = 0
        total_seeds = 0
        all_confidences = []

        for file_idx, file in enumerate(files):
            # Read and process image
            contents = await file.read()
            rgb_img = process_uploaded_image(contents)

            # Step 1: Detect seeds
            detected_seeds, (img_height, img_width) = detect_seeds(rgb_img)

            # Save image to storage (unique filename per image index)
            storage_path = save_image_to_storage(contents, scan_batch.id, file.filename or f"image_{file_idx}.jpg", image_index=file_idx)
            
            # Create scan image record
            scan_image = ScanImage(
                batch_id=scan_batch.id,
                storage_path=storage_path,
                original_filename=file.filename,
                width=img_width,
                height=img_height
            )
            db.add(scan_image)
            db.flush()

            # Step 2: Classify seeds (if any detected)
            if len(detected_seeds) > 0:
                classified_results = classify_seeds(rgb_img, detected_seeds)

                # Calculate statistics for this image
                good_count = sum(
                    1 for s in classified_results if s["quality"] == "Good"
                )
                bad_count = sum(1 for s in classified_results if s["quality"] == "Bad")

                # Save seed detections
                for seed_data in classified_results:
                    x1, y1, x2, y2 = seed_data["box"]
                    
                    # Normalize bounding box coordinates (0.0-1.0)
                    box_x_norm = x1 / img_width if img_width > 0 else 0.0
                    box_y_norm = y1 / img_height if img_height > 0 else 0.0
                    box_w_norm = (x2 - x1) / img_width if img_width > 0 else 0.0
                    box_h_norm = (y2 - y1) / img_height if img_height > 0 else 0.0
                    
                    detection = SeedDetection(
                        batch_id=scan_batch.id,
                        image_id=scan_image.id,
                        quality_label=QualityLabel.GOOD if seed_data["quality"] == "Good" else QualityLabel.BAD,
                        confidence_score=seed_data["classification_confidence"] / 100.0,  # Convert percentage to 0-1
                        detection_confidence=seed_data["detection_confidence"],
                        box_x_norm=box_x_norm,
                        box_y_norm=box_y_norm,
                        box_w_norm=box_w_norm,
                        box_h_norm=box_h_norm,
                        area=seed_data["area"],
                        width=seed_data["width"],
                        height=seed_data["height"],
                        aspect_ratio=seed_data["aspect_ratio"],
                        centroid_x=seed_data["centroid"]["x"],
                        centroid_y=seed_data["centroid"]["y"],
                        good_percentage=seed_data["good_percentage"],
                        bad_percentage=seed_data["bad_percentage"]
                    )
                    db.add(detection)
                    all_confidences.append(seed_data["classification_confidence"])

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
                            "width": seed["width"],
                            "height": seed["height"],
                            "area": seed["area"],
                            "aspect_ratio": seed["aspect_ratio"],
                            "centroid": seed["centroid"],
                            "quality": seed["quality"],
                            "detection_confidence": round(
                                seed["detection_confidence"], 4
                            ),
                            "good_percentage": seed["good_percentage"],
                            "bad_percentage": seed["bad_percentage"],
                            "classification_confidence": seed[
                                "classification_confidence"
                            ],
                            "raw_probability": seed["raw_probability"],
                            "color": (
                                "#FF0000" if seed["quality"] == "Bad" else "#00FF00"
                            ),
                        }
                    )

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
                    "good_percentage": (
                        round((good_count / len(bounding_boxes) * 100), 2)
                        if len(bounding_boxes) > 0
                        else 0
                    ),
                    "bad_percentage": (
                        round((bad_count / len(bounding_boxes) * 100), 2)
                        if len(bounding_boxes) > 0
                        else 0
                    ),
                },
                "image_dimensions": {"width": img_width, "height": img_height},
            }
            all_results.append(image_result)

        # Calculate overall statistics
        overall_good_pct = (
            round((total_good / total_seeds * 100), 2) if total_seeds > 0 else 0
        )
        overall_bad_pct = (
            round((total_bad / total_seeds * 100), 2) if total_seeds > 0 else 0
        )
        
        # Calculate average confidence
        avg_confidence = (
            sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        )

        # Update batch with final statistics
        processing_end = datetime.utcnow()
        processing_duration_ms = int((processing_end - processing_start).total_seconds() * 1000)
        
        scan_batch.status = ProcessingStatus.COMPLETED
        scan_batch.total_seeds = total_seeds
        scan_batch.bad_seeds_count = total_bad
        scan_batch.avg_confidence_score = avg_confidence / 100.0  # Convert to 0-1
        scan_batch.processing_end_at = processing_end
        scan_batch.processing_duration_ms = processing_duration_ms
        
        # Commit all changes
        db.commit()

        response_data = {
            "success": True,
            "batch_id": scan_batch.id,
            "mode": "accurate",
            "total_images": len(files),
            "total_seeds_all_images": total_seeds,
            "processing_duration_ms": processing_duration_ms,
            "overall_statistics": {
                "good_seeds": total_good,
                "bad_seeds": total_bad,
                "good_percentage": overall_good_pct,
                "bad_percentage": overall_bad_pct,
            },
            "results": all_results,
            "thresholds": {
                "detection_confidence": DETECTION_CONF_THRESHOLD,
                "classification_threshold": CLASSIFICATION_THRESHOLD,
            },
        }

        return JSONResponse(content=response_data)

    except ValueError as e:
        if 'db' in locals():
            db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        if 'db' in locals():
            db.rollback()
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
        if not file.content_type or not file.content_type.startswith("image/"):
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
                    "width": seed["width"],
                    "height": seed["height"],
                    "area": seed["area"],
                    "aspect_ratio": seed["aspect_ratio"],
                    "centroid": seed["centroid"],
                    "quality": seed["quality"],
                    "detection_confidence": round(seed["detection_confidence"], 4),
                    "good_percentage": seed["good_percentage"],
                    "bad_percentage": seed["bad_percentage"],
                    "classification_confidence": seed["classification_confidence"],
                    "raw_probability": seed["raw_probability"],
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


@app.post("/api/analyze-batch/fast")
async def analyze_batch_fast(files: List[UploadFile] = File(...)):
    """
    Fast batch analysis endpoint: Multiple images using Roboflow for detection + Local ResNet for classification
    """
    try:
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        # Validate all files are images
        for file in files:
            if not file.content_type or not file.content_type.startswith("image/"):
                raise HTTPException(
                    status_code=400, detail=f"File {file.filename} is not an image"
                )

        print(f"Processing {len(files)} images in batch (fast mode)...")

        # Process each image
        all_results = []
        total_good = 0
        total_bad = 0
        total_seeds = 0

        for file_idx, file in enumerate(files):
            # Read and process image
            contents = await file.read()
            rgb_img = process_uploaded_image(contents)
            orig_h, orig_w, _ = rgb_img.shape

            # Call Roboflow API
            img_base64 = base64.b64encode(contents).decode("utf-8")

            response = requests.post(
                ROBOFLOW_URL,
                data=img_base64,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                raise Exception(
                    f"Roboflow API Error for {file.filename}: {response.text}"
                )

            result = response.json()

            # Parse Roboflow results
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

            # Classify seeds if any detected
            if len(detected_seeds) > 0:
                classified_results = classify_seeds(rgb_img, detected_seeds)

                # Calculate statistics
                good_count = sum(
                    1 for s in classified_results if s["quality"] == "Good"
                )
                bad_count = sum(1 for s in classified_results if s["quality"] == "Bad")

                # Update totals
                total_good += good_count
                total_bad += bad_count
                total_seeds += len(classified_results)

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
                            "width": seed["width"],
                            "height": seed["height"],
                            "area": seed["area"],
                            "aspect_ratio": seed["aspect_ratio"],
                            "centroid": seed["centroid"],
                            "quality": seed["quality"],
                            "detection_confidence": round(
                                seed["detection_confidence"], 4
                            ),
                            "good_percentage": seed["good_percentage"],
                            "bad_percentage": seed["bad_percentage"],
                            "classification_confidence": seed[
                                "classification_confidence"
                            ],
                            "raw_probability": seed["raw_probability"],
                            "color": (
                                "#FF0000" if seed["quality"] == "Bad" else "#00FF00"
                            ),
                        }
                    )

                all_results.append(
                    {
                        "filename": file.filename,
                        "bounding_boxes": bounding_boxes,
                        "statistics": {
                            "total_seeds": len(classified_results),
                            "good_seeds": good_count,
                            "bad_seeds": bad_count,
                            "good_percentage": (
                                round((good_count / len(classified_results) * 100), 2)
                                if len(classified_results) > 0
                                else 0
                            ),
                            "bad_percentage": (
                                round((bad_count / len(classified_results) * 100), 2)
                                if len(classified_results) > 0
                                else 0
                            ),
                        },
                        "image_dimensions": {"width": orig_w, "height": orig_h},
                    }
                )
            else:
                # No seeds detected
                all_results.append(
                    {
                        "filename": file.filename,
                        "bounding_boxes": [],
                        "statistics": {
                            "total_seeds": 0,
                            "good_seeds": 0,
                            "bad_seeds": 0,
                            "good_percentage": 0.0,
                            "bad_percentage": 0.0,
                        },
                        "image_dimensions": {"width": orig_w, "height": orig_h},
                    }
                )

            print(
                f"  [{file_idx+1}/{len(files)}] {file.filename}: {len(detected_seeds)} seeds detected"
            )

        # Return batch results
        return JSONResponse(
            content={
                "success": True,
                "mode": "fast",
                "results": all_results,
                "overall_statistics": {
                    "total_images": len(files),
                    "total_seeds": total_seeds,
                    "total_good": total_good,
                    "total_bad": total_bad,
                    "overall_good_percentage": (
                        round((total_good / total_seeds * 100), 2)
                        if total_seeds > 0
                        else 0
                    ),
                    "overall_bad_percentage": (
                        round((total_bad / total_seeds * 100), 2)
                        if total_seeds > 0
                        else 0
                    ),
                },
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Fast batch analysis failed: {str(e)}"
        )


# ============================================================================
# GET Endpoints - History and Data Retrieval
# ============================================================================

@app.get("/api/batches")
async def list_batches(
    request: Request,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    status: Optional[str] = Query(None, description="Filter by status (PENDING, PROCESSING, COMPLETED, FAILED)"),
    db: Session = Depends(get_db)
):
    """
    List user's scan batches with pagination.
    
    Returns paginated list of batches for the current user (identified by device fingerprint).
    """
    # Extract device fingerprint
    user_agent = request.headers.get("user-agent", "")
    client_host = request.client.host if request.client else None
    device_fingerprint = generate_device_fingerprint(user_agent, client_host)
    
    # Get user
    user = get_user_by_fingerprint(db, device_fingerprint)
    if not user:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": "USER_NOT_FOUND",
                    "message": "User not found",
                    "details": None
                }
            }
        )
    
    # Get batches
    batches, total = get_user_batches(db, user.id, page, limit, status)
    
    # Calculate pagination info
    total_pages = (total + limit - 1) // limit if total > 0 else 1
    
    return {
        "success": True,
        "batches": batches,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


@app.get("/api/batches/{batch_id}")
async def get_batch_details(
    request: Request,
    batch_id: int = Path(..., description="Batch ID"),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific scan batch.
    
    Returns batch details including images and detection counts.
    """
    # Extract device fingerprint
    user_agent = request.headers.get("user-agent", "")
    client_host = request.client.host if request.client else None
    device_fingerprint = generate_device_fingerprint(user_agent, client_host)
    
    # Get user
    user = get_user_by_fingerprint(db, device_fingerprint)
    if not user:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": "USER_NOT_FOUND",
                    "message": "User not found",
                    "details": None
                }
            }
        )
    
    # Get batch with ownership verification
    batch = get_batch_by_id_and_user(db, batch_id, user.id)
    if not batch:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": "BATCH_NOT_FOUND",
                    "message": f"Batch with ID {batch_id} not found or access denied",
                    "details": None
                }
            }
        )
    
    # Get images for this batch
    images = db.query(ScanImage).filter(
        ScanImage.batch_id == batch.id
    ).order_by(ScanImage.created_at.asc()).all()
    
    # Format images with detection counts
    formatted_images = []
    for img in images:
        detection_count = db.query(func.count(SeedDetection.id)).filter(
            SeedDetection.image_id == img.id
        ).scalar() or 0
        
        # Use image ID in URL so each image has a unique URL (avoids same filename for multiple images)
        image_url = f"/api/images/{batch.id}/by-id/{img.id}"
        
        formatted_images.append({
            "id": img.id,
            "storage_path": img.storage_path,
            "original_filename": img.original_filename,
            "width": img.width,
            "height": img.height,
            "url": image_url,
            "detection_count": detection_count,
            "created_at": img.created_at.isoformat() if img.created_at else None
        })
    
    # Calculate good seeds count and percentages
    good_seeds_count = batch.total_seeds - batch.bad_seeds_count if batch.total_seeds else 0
    good_percentage = 0.0
    bad_percentage = 0.0
    if batch.total_seeds > 0:
        good_percentage = round((good_seeds_count / batch.total_seeds) * 100, 2)
        bad_percentage = round((batch.bad_seeds_count / batch.total_seeds) * 100, 2)
    
    return {
        "success": True,
        "batch": {
            "id": batch.id,
            "status": batch.status.value if batch.status else None,
            "total_seeds": batch.total_seeds,
            "bad_seeds_count": batch.bad_seeds_count,
            "good_seeds_count": good_seeds_count,
            "good_percentage": good_percentage,
            "bad_percentage": bad_percentage,
            "avg_confidence_score": batch.avg_confidence_score,
            "processing_duration_ms": batch.processing_duration_ms,
            "processing_start_at": batch.processing_start_at.isoformat() if batch.processing_start_at else None,
            "processing_end_at": batch.processing_end_at.isoformat() if batch.processing_end_at else None,
            "created_at": batch.created_at.isoformat() if batch.created_at else None,
            "error_message": batch.error_message,
            "images": formatted_images
        }
    }


@app.get("/api/batches/{batch_id}/detections")
async def get_batch_detections_endpoint(
    request: Request,
    batch_id: int = Path(..., description="Batch ID"),
    image_id: Optional[int] = Query(None, description="Filter by image ID"),
    quality: Optional[str] = Query(None, description="Filter by quality (GOOD, BAD)"),
    limit: int = Query(10000, ge=1, le=50000, description="Maximum number of detections to return"),
    db: Session = Depends(get_db)
):
    """
    Get all seed detections for a batch.
    
    Returns all detections with optional filtering by image_id or quality.
    """
    # Extract device fingerprint
    user_agent = request.headers.get("user-agent", "")
    client_host = request.client.host if request.client else None
    device_fingerprint = generate_device_fingerprint(user_agent, client_host)
    
    # Get user
    user = get_user_by_fingerprint(db, device_fingerprint)
    if not user:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": "USER_NOT_FOUND",
                    "message": "User not found",
                    "details": None
                }
            }
        )
    
    # Validate quality filter if provided
    if quality:
        try:
            QualityLabel(quality.upper())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "error": {
                        "code": "INVALID_QUALITY",
                        "message": f"Invalid quality filter: {quality}. Must be GOOD or BAD",
                        "details": None
                    }
                }
            )
    
    # Get detections
    detections = get_batch_detections(db, batch_id, user.id, image_id, quality, limit)
    
    # Verify batch exists (for 404 if batch doesn't exist)
    batch = get_batch_by_id_and_user(db, batch_id, user.id)
    if not batch:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "error": {
                    "code": "BATCH_NOT_FOUND",
                    "message": f"Batch with ID {batch_id} not found or access denied",
                    "details": None
                }
            }
        )
    
    return {
        "success": True,
        "batch_id": batch_id,
        "image_id": image_id,
        "total_detections": len(detections),
        "detections": detections
    }


@app.get("/api/stats")
async def get_user_statistics_endpoint(
    request: Request,
    days: Optional[int] = Query(None, ge=1, description="Number of days to look back"),
    db: Session = Depends(get_db)
):
    """
    Get aggregated statistics for the current user.
    
    Returns overall statistics including total batches, seeds analyzed, and averages.
    """
    # Extract device fingerprint
    user_agent = request.headers.get("user-agent", "")
    client_host = request.client.host if request.client else None
    device_fingerprint = generate_device_fingerprint(user_agent, client_host)
    
    # Get user
    user = get_user_by_fingerprint(db, device_fingerprint)
    if not user:
        # Return empty stats instead of 404 for better UX
        empty_stats = {
            "total_batches": 0,
            "total_seeds_analyzed": 0,
            "total_good_seeds": 0,
            "total_bad_seeds": 0,
            "overall_good_percentage": 0.0,
            "overall_bad_percentage": 0.0,
            "avg_seeds_per_batch": 0.0,
            "avg_confidence_score": 0.0,
            "avg_processing_time_ms": 0.0,
            "batches_by_status": {
                "COMPLETED": 0,
                "FAILED": 0,
                "PENDING": 0,
                "PROCESSING": 0
            },
            "recent_activity": {
                "batches_last_7_days": 0,
                "batches_last_30_days": 0
            },
            "period": {
                "days": days,
                "start_date": datetime.utcnow().isoformat(),
                "end_date": datetime.utcnow().isoformat()
            }
        }
        return {
            "success": True,
            "stats": empty_stats,
            "period": empty_stats.get("period", {})
        }
    
    # Get statistics
    try:
        stats = get_user_statistics(db, user.id, days)
        return {
            "success": True,
            "stats": stats,
            "period": stats.get("period", {})
        }
    except Exception as e:
        # Log error and return empty stats
        import traceback
        print(f"Error getting statistics: {e}")
        traceback.print_exc()
        empty_stats = {
            "total_batches": 0,
            "total_seeds_analyzed": 0,
            "total_good_seeds": 0,
            "total_bad_seeds": 0,
            "overall_good_percentage": 0.0,
            "overall_bad_percentage": 0.0,
            "avg_seeds_per_batch": 0.0,
            "avg_confidence_score": 0.0,
            "avg_processing_time_ms": 0.0,
            "batches_by_status": {
                "COMPLETED": 0,
                "FAILED": 0,
                "PENDING": 0,
                "PROCESSING": 0
            },
            "recent_activity": {
                "batches_last_7_days": 0,
                "batches_last_30_days": 0
            },
            "period": {
                "days": days,
                "start_date": datetime.utcnow().isoformat(),
                "end_date": datetime.utcnow().isoformat()
            }
        }
        return {
            "success": True,
            "stats": empty_stats,
            "period": empty_stats.get("period", {})
        }


@app.options("/api/images/{batch_id}/{path:path}")
async def serve_image_options(batch_id: int, path: str):
    """Handle CORS preflight for image endpoints."""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
    )


@app.get("/api/images/{batch_id}/by-id/{image_id}")
async def serve_image_by_id(
    request: Request,
    batch_id: int = Path(..., description="Batch ID"),
    image_id: int = Path(..., description="ScanImage ID"),
    db: Session = Depends(get_db)
):
    """
    Serve a stored image by batch ID and image ID.
    Uses storage_path from DB so each image is unique regardless of filename.
    """
    user_agent = request.headers.get("user-agent", "")
    client_host = request.client.host if request.client else None
    device_fingerprint = generate_device_fingerprint(user_agent, client_host)
    
    user = get_user_by_fingerprint(db, device_fingerprint)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    batch = get_batch_by_id_and_user(db, batch_id, user.id)
    if not batch:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Look up image by ID and batch (ensures it belongs to this batch)
    image = db.query(ScanImage).filter(
        ScanImage.id == image_id,
        ScanImage.batch_id == batch_id
    ).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    file_path = image.storage_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image file not found")
    
    filename = os.path.basename(file_path)
    content_type = "image/jpeg"
    if filename.lower().endswith('.png'):
        content_type = "image/png"
    elif filename.lower().endswith('.gif'):
        content_type = "image/gif"
    elif filename.lower().endswith('.webp'):
        content_type = "image/webp"
    
    with open(file_path, "rb") as f:
        file_contents = f.read()
    
    return Response(
        content=file_contents,
        media_type=content_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Content-Disposition": f'inline; filename="{filename}"',
        }
    )


@app.get("/api/images/{batch_id}/{filename}")
async def serve_image(
    request: Request,
    batch_id: int = Path(..., description="Batch ID"),
    filename: str = Path(..., description="Image filename"),
    db: Session = Depends(get_db)
):
    """
    Serve stored image files by filename (e.g. for history thumbnails).
    Security: Verifies batch ownership before serving images.
    """
    user_agent = request.headers.get("user-agent", "")
    client_host = request.client.host if request.client else None
    device_fingerprint = generate_device_fingerprint(user_agent, client_host)
    
    user = get_user_by_fingerprint(db, device_fingerprint)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    batch = get_batch_by_id_and_user(db, batch_id, user.id)
    if not batch:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if '..' in filename or '/' in filename or '\\' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_path = os.path.join("uploads", "batches", str(batch_id), filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    content_type = "image/jpeg"
    if filename.lower().endswith('.png'):
        content_type = "image/png"
    elif filename.lower().endswith('.gif'):
        content_type = "image/gif"
    elif filename.lower().endswith('.webp'):
        content_type = "image/webp"
    
    with open(file_path, "rb") as f:
        file_contents = f.read()
    
    return Response(
        content=file_contents,
        media_type=content_type,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Content-Disposition": f'inline; filename="{filename}"',
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        timeout_keep_alive=600  # 10 minutes keep-alive timeout for long-running requests
    )
