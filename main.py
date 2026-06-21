from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from typing import Optional
import torch
import cv2
import numpy as np
import albumentations as A
from albumentations.pytorch import ToTensorV2
from torchvision import transforms
from typing import List, Dict
import os
import base64
import requests
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func

# Database imports
from app.database import get_db
from app.models import ScanBatch, ScanImage, SeedDetection, ProcessingStatus, QualityLabel
from app.ml.model_manager import ModelManager
from app.ml.detection_pipeline import detect_seeds_multi, classify_seeds_multi
from app.limits import enforce_rate_limit, guard_upload_size, guard_batch_count
from app.observability import configure_logging, RequestContextMiddleware
from app.crud import (
    get_or_create_guest_user,
    generate_device_fingerprint,
    get_user_by_fingerprint,
    get_user_batches,
    get_batch_by_id_and_user,
    get_batch_detections,
    get_user_statistics,
    get_user_analytics,
    compare_batches,
    iter_batch_detections_for_export,
    delete_batch,
    delete_batches_bulk,
    create_share_token,
    revoke_share_token,
    get_shared_batch,
)


def utcnow() -> datetime:
    """Timezone-aware current UTC time (replaces the deprecated datetime.utcnow())."""
    return datetime.now(timezone.utc)


app = FastAPI(title="Bank Seed Demo API", version="1.0.0")

# Structured logging + request-id/timing middleware (#15).
log = configure_logging(os.getenv("LOG_LEVEL", "INFO"))
app.add_middleware(RequestContextMiddleware)

# CORS middleware for frontend access.
# Origins are configurable via CORS_ORIGINS (comma-separated). Default "*" allows any
# origin; in that mode credentials are disabled because the CORS spec forbids combining
# a wildcard Access-Control-Allow-Origin with Access-Control-Allow-Credentials (#6).
_cors_env = os.getenv("CORS_ORIGINS", "*").strip()
if _cors_env == "*":
    _cors_origins = ["*"]
    _cors_allow_credentials = False
else:
    _cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
    _cors_allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Roboflow config for the "fast" endpoints. The API key MUST come from the environment
# (ROBOFLOW_API_KEY); it is no longer hardcoded (#3). When unset, the fast endpoints
# return 503 instead of leaking/clashing on a baked-in key.
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "")
ROBOFLOW_MODEL_ID = os.getenv("ROBOFLOW_MODEL_ID", "maize-gslkp-3pcv5/9")
ROBOFLOW_URL = (
    f"https://detect.roboflow.com/{ROBOFLOW_MODEL_ID}?api_key={ROBOFLOW_API_KEY}"
    if ROBOFLOW_API_KEY else None
)


def _require_roboflow():
    """Raise 503 if the fast (Roboflow-backed) endpoints are not configured."""
    if not ROBOFLOW_URL:
        raise HTTPException(
            status_code=503,
            detail="Fast mode is not configured: set the ROBOFLOW_API_KEY environment variable.",
        )


# Global variables for models
model_manager: Optional[ModelManager] = None
device = None

# Configuration
NMS_THRESHOLD = 0.3
IMAGE_SIZE = 224

# Note: Thresholds are now loaded from database via ModelManager
# - Detection threshold: from ai_models table (type='detection')
# - Quality thresholds: from ai_models table per seed type (type='quality')

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
    """Load all models on startup using ModelManager"""
    global model_manager, device
    
    device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
    print(f"Using device: {device}")
    
    # Import here to avoid circular dependencies
    from app.database import SessionLocal
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Initialize model manager (loads all active models from database)
        model_manager = ModelManager(db, device)
        
        print("\n" + "="*50)
        print("MODEL CONFIGURATION")
        print("="*50)
        config = model_manager.get_config_summary()
        print(f"Detection: {config['detection_model']['name']} (v{config['detection_model']['version']})")
        print("Quality Models:")
        for seed_type, model_info in config['quality_models'].items():
            print(f"  - {seed_type}: {model_info['name']} (threshold={model_info['threshold']})")
        print("="*50 + "\n")
        
    finally:
        db.close()


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
    """
    Run object detection with 3-class output (background, coffee, maize).
    Returns detected seeds with seed type information.
    """
    return detect_seeds_multi(
        rgb_img, 
        model_manager, 
        device, 
        detection_transform, 
        NMS_THRESHOLD, 
        IMAGE_SIZE
    )


def classify_seeds(rgb_img: np.ndarray, detected_seeds: List[Dict]) -> List[Dict]:
    """
    Classify each detected seed using the appropriate quality model based on seed type.
    Routes to coffee or maize model automatically.
    """
    return classify_seeds_multi(
        rgb_img, 
        detected_seeds, 
        model_manager, 
        device, 
        classification_transform
    )


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "Seed Quality Detection API",
        "models_loaded": model_manager is not None,
        "device": str(device),
    }


@app.get("/health")
async def health():
    """Liveness probe: the process is up and serving (no dependency checks)."""
    return {"status": "ok"}


@app.get("/readiness")
async def readiness(db: Session = Depends(get_db)):
    """Readiness probe: verifies DB connectivity and that models are loaded.

    Returns 503 when a dependency is not ready (so orchestrators hold traffic).
    """
    from sqlalchemy import text

    checks = {"database": False, "models": model_manager is not None}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        log.warning("readiness db check failed", extra={"path": "/readiness"})
        checks["database"] = False
        _ = e

    ready = all(checks.values())
    payload = {"ready": ready, "checks": checks, "device": str(device)}
    if not ready:
        return JSONResponse(status_code=503, content=payload)
    return payload


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

        # Rate limit per device (#16)
        enforce_rate_limit(device_fingerprint)

        # Get or create guest user (will reuse if fingerprint matches)
        guest_user = get_or_create_guest_user(db, device_fingerprint)

        # Create scan batch
        processing_start = utcnow()
        scan_batch = ScanBatch(
            user_id=guest_user.id,
            status=ProcessingStatus.PROCESSING,
            processing_start_at=processing_start
        )
        db.add(scan_batch)
        db.flush()

        # Read and process image
        contents = await file.read()
        guard_upload_size(contents, file.filename or "")
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
            processing_end = utcnow()
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
                seed_type_id=seed_data["seed_type_id"],
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
        processing_end = utcnow()
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
                    "seed_type": seed["seed_type_name"],
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
            "thresholds": model_manager.get_config_summary() if model_manager else {},
        }

        return JSONResponse(content=response_data)

    except HTTPException:
        # Deliberate client errors (e.g. 400 invalid file) must not be masked as 500.
        if 'db' in locals():
            db.rollback()
        raise
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

        # Guard batch size (#16)
        guard_batch_count(files)

        # Extract device fingerprint from request headers
        user_agent = request.headers.get("user-agent", "")
        client_host = request.client.host if request.client else None
        device_fingerprint = generate_device_fingerprint(user_agent, client_host)

        # Rate limit per device (#16)
        enforce_rate_limit(device_fingerprint)

        # Get or create guest user (will reuse if fingerprint matches)
        guest_user = get_or_create_guest_user(db, device_fingerprint)

        # Create scan batch for the entire batch
        processing_start = utcnow()
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
            guard_upload_size(contents, file.filename or "")
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
                seed_type_id=seed_data["seed_type_id"],
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
                            "seed_type": seed["seed_type_name"],
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
        processing_end = utcnow()
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
            "thresholds": model_manager.get_config_summary() if model_manager else {},
        }

        return JSONResponse(content=response_data)

    except HTTPException:
        if 'db' in locals():
            db.rollback()
        raise
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
    if model_manager is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    config = model_manager.get_config_summary()
    
    return {
        "detection_model": config["detection_model"],
        "quality_models": config["quality_models"],
        "nms_threshold": NMS_THRESHOLD,
        "image_size": IMAGE_SIZE,
        "device": str(device),
    }




@app.get("/api/models/config")
async def get_models_config():
    """Get active model configurations from database"""
    if model_manager is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    return model_manager.get_config_summary()


@app.post("/api/analyze/fast")
async def analyze_image_fast(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Fast endpoint using Roboflow for detection + Local ResNet for classification.
    Now persists results like the other analyze endpoints and returns a batch_id (#7).
    """
    try:
        _require_roboflow()
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        # Resolve user + create a batch so fast results show up in history/stats (#7).
        user_agent = request.headers.get("user-agent", "")
        client_host = request.client.host if request.client else None
        device_fingerprint = generate_device_fingerprint(user_agent, client_host)
        guest_user = get_or_create_guest_user(db, device_fingerprint)
        processing_start = utcnow()
        scan_batch = ScanBatch(
            user_id=guest_user.id,
            status=ProcessingStatus.PROCESSING,
            processing_start_at=processing_start,
        )
        db.add(scan_batch)
        db.flush()

        # Read image
        contents = await file.read()
        guard_upload_size(contents, file.filename or "")
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

                # Get class name and ID
                class_name = pred["class"].lower()
                seed_type_id = None
                if model_manager:
                    try:
                        seed_type_id = model_manager.get_seed_type_id(class_name)
                    except Exception:
                        seed_type_id = None  # Keep None if not found

                # Skip classes we have no quality model for; classifying them would
                # raise downstream and 500 the whole request (#8).
                if seed_type_id is None:
                    print(f"Skipping unmapped detection class '{class_name}' (fast mode)")
                    continue

                detected_seeds.append(
                    {
                        "box": (x1, y1, x2, y2),
                        "detection_confidence": float(pred["confidence"]),
                        "seed_type_name": class_name,
                        "seed_type_id": seed_type_id,
                    }
                )
        # Persist the uploaded image regardless of detections.
        storage_path = save_image_to_storage(contents, scan_batch.id, file.filename or "image.jpg")
        scan_image = ScanImage(
            batch_id=scan_batch.id,
            storage_path=storage_path,
            original_filename=file.filename,
            width=orig_w,
            height=orig_h,
        )
        db.add(scan_image)
        db.flush()

        if len(detected_seeds) == 0:
            processing_end = utcnow()
            scan_batch.status = ProcessingStatus.COMPLETED
            scan_batch.processing_end_at = processing_end
            scan_batch.processing_duration_ms = int((processing_end - processing_start).total_seconds() * 1000)
            db.commit()
            return JSONResponse(
                content={
                    "success": True,
                    "mode": "fast",
                    "batch_id": scan_batch.id,
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

        # Persist detections + format bounding boxes
        bounding_boxes = []
        confidences = []
        for idx, seed in enumerate(classified_results):
            x1, y1, x2, y2 = seed["box"]
            box_x_norm = x1 / orig_w if orig_w > 0 else 0.0
            box_y_norm = y1 / orig_h if orig_h > 0 else 0.0
            box_w_norm = (x2 - x1) / orig_w if orig_w > 0 else 0.0
            box_h_norm = (y2 - y1) / orig_h if orig_h > 0 else 0.0
            db.add(SeedDetection(
                batch_id=scan_batch.id,
                image_id=scan_image.id,
                seed_type_id=seed["seed_type_id"],
                quality_label=QualityLabel.GOOD if seed["quality"] == "Good" else QualityLabel.BAD,
                confidence_score=seed["classification_confidence"] / 100.0,
                detection_confidence=seed["detection_confidence"],
                box_x_norm=box_x_norm, box_y_norm=box_y_norm,
                box_w_norm=box_w_norm, box_h_norm=box_h_norm,
                area=seed["area"], width=seed["width"], height=seed["height"],
                aspect_ratio=seed["aspect_ratio"],
                centroid_x=seed["centroid"]["x"], centroid_y=seed["centroid"]["y"],
                good_percentage=seed["good_percentage"], bad_percentage=seed["bad_percentage"],
            ))
            confidences.append(seed["classification_confidence"])
            bounding_boxes.append(
                {
                    "id": idx,
                    "seed_type": seed["seed_type_name"],
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
                    "color": "#FF0000" if seed["quality"] == "Bad" else "#00FF00",
                }
            )

        # Finalize batch
        processing_end = utcnow()
        scan_batch.status = ProcessingStatus.COMPLETED
        scan_batch.total_seeds = total_count
        scan_batch.bad_seeds_count = bad_count
        scan_batch.avg_confidence_score = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
        scan_batch.processing_end_at = processing_end
        scan_batch.processing_duration_ms = int((processing_end - processing_start).total_seconds() * 1000)
        db.commit()

        return JSONResponse(
            content={
                "success": True,
                "mode": "fast",
                "batch_id": scan_batch.id,
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

    except HTTPException:
        if 'db' in locals():
            db.rollback()
        raise
    except Exception as e:
        if 'db' in locals():
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Fast analysis failed: {str(e)}")





@app.post("/api/analyze-batch/fast")
async def analyze_batch_fast(
    request: Request,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Fast batch analysis endpoint: Multiple images using Roboflow for detection + Local ResNet for classification
    """
    try:
        _require_roboflow()
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        # Guard batch size (#16)
        guard_batch_count(files)

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
        processing_start = utcnow()
        scan_batch = ScanBatch(
            user_id=guest_user.id,
            status=ProcessingStatus.PROCESSING,
            processing_start_at=processing_start
        )
        db.add(scan_batch)
        db.flush()

        print(f"Processing {len(files)} images in batch (fast mode)...")

        # Process each image
        all_results = []
        total_good = 0
        total_bad = 0
        total_seeds = 0
        all_confidences = []

        for file_idx, file in enumerate(files):
            # Read and process image
            contents = await file.read()
            guard_upload_size(contents, file.filename or "")
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
                    
                    # Get class name and ID
                    class_name = pred["class"].lower()
                    seed_type_id = None
                    if model_manager:
                        try:
                            seed_type_id = model_manager.get_seed_type_id(class_name)
                        except Exception:
                            seed_type_id = None  # Keep None if not found

                    # Skip classes we have no quality model for (#8).
                    if seed_type_id is None:
                        print(f"Skipping unmapped detection class '{class_name}' (fast batch)")
                        continue

                    detected_seeds.append(
                        {
                            "box": (x1, y1, x2, y2),
                            "detection_confidence": float(pred["confidence"]),
                            "seed_type_name": class_name,
                            "seed_type_id": seed_type_id,
                        }
                    )

            # Save image to storage (unique filename per image index)
            storage_path = save_image_to_storage(contents, scan_batch.id, file.filename or f"image_{file_idx}.jpg", image_index=file_idx)
            
            # Create scan image record
            scan_image = ScanImage(
                batch_id=scan_batch.id,
                storage_path=storage_path,
                original_filename=file.filename,
                width=orig_w,
                height=orig_h
            )
            db.add(scan_image)
            db.flush()

            # Classify seeds if any detected
            if len(detected_seeds) > 0:
                classified_results = classify_seeds(rgb_img, detected_seeds)

                # Calculate statistics
                good_count = sum(
                    1 for s in classified_results if s["quality"] == "Good"
                )
                bad_count = sum(1 for s in classified_results if s["quality"] == "Bad")

                # Save seed detections
                for seed_data in classified_results:
                    x1, y1, x2, y2 = seed_data["box"]
                    
                    # Normalize bounding box coordinates (0.0-1.0)
                    box_x_norm = x1 / orig_w if orig_w > 0 else 0.0
                    box_y_norm = y1 / orig_h if orig_h > 0 else 0.0
                    box_w_norm = (x2 - x1) / orig_w if orig_w > 0 else 0.0
                    box_h_norm = (y2 - y1) / orig_h if orig_h > 0 else 0.0
                    
                    detection = SeedDetection(
                        batch_id=scan_batch.id,
                        image_id=scan_image.id,
                        seed_type_id=seed_data["seed_type_id"],
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
                            "seed_type": seed["seed_type_name"],
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
                            "color": (
                                "#FF0000" if seed["quality"] == "Bad" else "#00FF00"
                            ),
                        }
                    )

                all_results.append(
                    {
                        "filename": file.filename,
                        "image_index": file_idx,
                        "total_seeds": len(classified_results),
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
                        "image_index": file_idx,
                        "total_seeds": 0,
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
        processing_end = utcnow()
        processing_duration_ms = int((processing_end - processing_start).total_seconds() * 1000)
        
        scan_batch.status = ProcessingStatus.COMPLETED
        scan_batch.total_seeds = total_seeds
        scan_batch.bad_seeds_count = total_bad
        scan_batch.avg_confidence_score = avg_confidence / 100.0  # Convert to 0-1
        scan_batch.processing_end_at = processing_end
        scan_batch.processing_duration_ms = processing_duration_ms
        
        # Commit all changes
        db.commit()

        # Return batch results
        return JSONResponse(
            content={
                "success": True,
                "batch_id": scan_batch.id,
                "mode": "fast",
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
                "thresholds": model_manager.get_config_summary() if model_manager else {},
            }
        )

    except HTTPException:
        if 'db' in locals():
            db.rollback()
        raise
    except Exception as e:
        if 'db' in locals():
            db.rollback()
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
    sort: str = Query("created_at", pattern="^(created_at|total_seeds|good_percentage|avg_confidence_score|bad_seeds_count)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    date_from: Optional[str] = Query(None, description="ISO date lower bound on created_at"),
    date_to: Optional[str] = Query(None, description="ISO date upper bound on created_at"),
    min_seeds: Optional[int] = Query(None, ge=0, description="Minimum total seeds"),
    db: Session = Depends(get_db)
):
    """
    List user's scan batches with pagination, sorting and filtering (#19).

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
    batches, total = get_user_batches(
        db, user.id, page, limit, status,
        sort=sort, order=order, date_from=date_from, date_to=date_to, min_seeds=min_seeds,
    )
    
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


@app.delete("/api/batches/{batch_id}")
async def delete_batch_endpoint(
    request: Request,
    batch_id: int = Path(..., description="Batch ID"),
    db: Session = Depends(get_db),
):
    """Delete a batch (cascades images + detections + on-disk files) (#18)."""
    user_agent = request.headers.get("user-agent", "")
    client_host = request.client.host if request.client else None
    user = get_user_by_fingerprint(db, generate_device_fingerprint(user_agent, client_host))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not delete_batch(db, batch_id, user.id):
        raise HTTPException(status_code=404, detail="Batch not found or access denied")
    return {"success": True, "deleted": batch_id}


@app.post("/api/batches/delete")
async def bulk_delete_batches_endpoint(
    request: Request,
    payload: dict,
    db: Session = Depends(get_db),
):
    """Delete multiple owned batches. Body: {"batch_ids": [int, ...]} (#18)."""
    batch_ids = payload.get("batch_ids") if isinstance(payload, dict) else None
    if not batch_ids or not isinstance(batch_ids, list):
        raise HTTPException(status_code=400, detail="batch_ids (non-empty list) is required")
    try:
        batch_ids = [int(b) for b in batch_ids]
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="batch_ids must be integers")

    user_agent = request.headers.get("user-agent", "")
    client_host = request.client.host if request.client else None
    user = get_user_by_fingerprint(db, generate_device_fingerprint(user_agent, client_host))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = delete_batches_bulk(db, batch_ids, user.id)
    return {"success": True, **result, "deleted_count": len(result["deleted"])}


@app.post("/api/batches/{batch_id}/share")
async def share_batch(
    request: Request,
    batch_id: int = Path(..., description="Batch ID"),
    db: Session = Depends(get_db),
):
    """Create a public read-only share token for an owned batch (#21)."""
    user = _current_user(request, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    token = create_share_token(db, batch_id, user.id)
    if not token:
        raise HTTPException(status_code=404, detail="Batch not found or access denied")
    return {"success": True, "share_token": token, "share_path": f"/api/shared/{token}"}


@app.delete("/api/batches/{batch_id}/share")
async def unshare_batch(
    request: Request,
    batch_id: int = Path(..., description="Batch ID"),
    db: Session = Depends(get_db),
):
    """Revoke a batch's share token (#21)."""
    user = _current_user(request, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not revoke_share_token(db, batch_id, user.id):
        raise HTTPException(status_code=404, detail="Batch not found or access denied")
    return {"success": True, "revoked": batch_id}


@app.get("/api/shared/{token}")
async def get_shared(token: str = Path(..., description="Public share token"), db: Session = Depends(get_db)):
    """Read-only batch report for a valid share token (no fingerprint required) (#21)."""
    data = get_shared_batch(db, token)
    if not data:
        raise HTTPException(status_code=404, detail="Shared report not found")
    return {"success": True, "batch": data}


@app.get("/api/batches/{batch_id}/images/{image_id}/annotated.png")
async def annotated_image(
    request: Request,
    batch_id: int = Path(...),
    image_id: int = Path(...),
    db: Session = Depends(get_db),
):
    """Server-render the stored image with bounding boxes + labels burned in (#20)."""
    user = _current_user(request, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    batch = get_batch_by_id_and_user(db, batch_id, user.id)
    if not batch:
        raise HTTPException(status_code=403, detail="Access denied")
    image = db.query(ScanImage).filter(
        ScanImage.id == image_id, ScanImage.batch_id == batch_id
    ).first()
    if not image or not os.path.exists(image.storage_path):
        raise HTTPException(status_code=404, detail="Image not found")

    img = cv2.imread(image.storage_path)  # BGR
    if img is None:
        raise HTTPException(status_code=500, detail="Failed to read stored image")
    h, w = img.shape[:2]

    detections = db.query(SeedDetection).filter(
        SeedDetection.image_id == image_id, SeedDetection.batch_id == batch_id
    ).all()
    for d in detections:
        x1 = int(d.box_x_norm * w)
        y1 = int(d.box_y_norm * h)
        x2 = int((d.box_x_norm + d.box_w_norm) * w)
        y2 = int((d.box_y_norm + d.box_h_norm) * h)
        is_bad = d.quality_label == QualityLabel.BAD
        color = (0, 0, 255) if is_bad else (0, 200, 0)  # BGR red/green
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        label = (d.seed_type.name[:1].upper() if d.seed_type else "?") + ("/B" if is_bad else "/G")
        cv2.putText(img, label, (x1, max(0, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)

    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to encode annotated image")
    return Response(
        content=buf.tobytes(),
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="batch_{batch_id}_image_{image_id}_annotated.png"',
            "Access-Control-Allow-Origin": "*",
        },
    )


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
                "start_date": utcnow().isoformat(),
                "end_date": utcnow().isoformat()
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
                "start_date": utcnow().isoformat(),
                "end_date": utcnow().isoformat()
            }
        }
        return {
            "success": True,
            "stats": empty_stats,
            "period": empty_stats.get("period", {})
        }


def _current_user(request: Request, db: Session):
    """Resolve the current guest user from the request's device fingerprint (read-only)."""
    user_agent = request.headers.get("user-agent", "")
    client_host = request.client.host if request.client else None
    fingerprint = generate_device_fingerprint(user_agent, client_host)
    return get_user_by_fingerprint(db, fingerprint)


@app.get("/api/analytics")
async def get_analytics(
    request: Request,
    days: Optional[int] = Query(None, ge=1, description="Look-back window in days"),
    db: Session = Depends(get_db),
):
    """Rich analytics for the analytics dashboard.

    Returns totals, a daily good/bad trend, the seed-type split, and size/confidence
    histograms — all computed from the current user's persisted detections.
    """
    user = _current_user(request, db)
    if not user:
        # No history yet -> return a well-formed empty payload (better UX than 404).
        # user_id=-1 matches no rows, so get_user_analytics returns its empty shape.
        return {"success": True, "analytics": get_user_analytics(db, -1, days)}
    analytics = get_user_analytics(db, user.id, days)
    return {"success": True, "analytics": analytics}


@app.post("/api/compare")
async def compare(
    request: Request,
    payload: dict,
    db: Session = Depends(get_db),
):
    """Compare multiple batches side-by-side. Body: {"batch_ids": [int, ...]}."""
    batch_ids = payload.get("batch_ids") if isinstance(payload, dict) else None
    if not batch_ids or not isinstance(batch_ids, list):
        raise HTTPException(status_code=400, detail="batch_ids (non-empty list) is required")
    if len(batch_ids) > 10:
        raise HTTPException(status_code=400, detail="Cannot compare more than 10 batches at once")
    try:
        batch_ids = [int(b) for b in batch_ids]
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="batch_ids must be integers")

    user = _current_user(request, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    summaries = compare_batches(db, user.id, batch_ids)
    if not summaries:
        raise HTTPException(status_code=404, detail="None of the requested batches were found")
    return {"success": True, "count": len(summaries), "batches": summaries}


@app.get("/api/batches/{batch_id}/export.csv")
async def export_batch_csv(
    request: Request,
    batch_id: int = Path(..., description="Batch ID"),
    db: Session = Depends(get_db),
):
    """Download all detections for a batch as CSV."""
    user = _current_user(request, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    rows = iter_batch_detections_for_export(db, batch_id, user.id)
    if rows is None:
        raise HTTPException(status_code=404, detail="Batch not found or access denied")

    import csv as _csv
    import io as _io

    buf = _io.StringIO()
    fieldnames = [
        "detection_id", "image_id", "seed_type", "quality", "confidence_score",
        "detection_confidence", "good_percentage", "bad_percentage",
        "box_x_norm", "box_y_norm", "box_w_norm", "box_h_norm",
        "area", "width", "height", "aspect_ratio", "centroid_x", "centroid_y",
    ]
    writer = _csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)
    csv_text = buf.getvalue()

    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="batch_{batch_id}_detections.csv"',
            "Access-Control-Allow-Origin": "*",
        },
    )


@app.get("/api/batches/{batch_id}/export.json")
async def export_batch_json(
    request: Request,
    batch_id: int = Path(..., description="Batch ID"),
    db: Session = Depends(get_db),
):
    """Download all detections for a batch as JSON."""
    user = _current_user(request, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    rows = iter_batch_detections_for_export(db, batch_id, user.id)
    if rows is None:
        raise HTTPException(status_code=404, detail="Batch not found or access denied")

    return JSONResponse(
        content={"batch_id": batch_id, "total_detections": len(rows), "detections": rows},
        headers={
            "Content-Disposition": f'attachment; filename="batch_{batch_id}_detections.json"',
        },
    )


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
