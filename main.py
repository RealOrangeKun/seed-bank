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
detection_transform = A.Compose([
    A.Resize(224, 224),
    A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ToTensorV2()
])

classification_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])


@app.on_event("startup")
async def load_models():
    """Load both models on startup"""
    global detection_model, classification_model, device
    
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    print(f"Using device: {device}")
    
    # Load Faster R-CNN detection model
    detection_model_path = "models/FasterRCNN_ResNet50_Final.pth"
    if not os.path.exists(detection_model_path):
        raise Exception(f"Detection model not found at {detection_model_path}")
    
    detection_model = torchvision.models.detection.fasterrcnn_resnet50_fpn(weights=None)
    num_ftrs = detection_model.roi_heads.box_predictor.cls_score.in_features
    detection_model.roi_heads.box_predictor = FastRCNNPredictor(num_ftrs, 2)
    detection_model.load_state_dict(torch.load(detection_model_path, map_location=device))
    detection_model.to(device)
    detection_model.eval()
    print("✓ Detection model loaded successfully")
    
    # Load ResNet50 classification model
    classification_model_path = "models/ResNet50_maize_seeds_NEW.pth"
    if not os.path.exists(classification_model_path):
        raise Exception(f"Classification model not found at {classification_model_path}")
    
    classification_model = models.resnet50(weights=None)
    num_ftrs = classification_model.fc.in_features
    classification_model.fc = nn.Sequential(
        nn.Linear(num_ftrs, 1),
        nn.Sigmoid()
    )
    classification_model.load_state_dict(torch.load(classification_model_path, map_location=device))
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
    img_tensor = transformed['image'].unsqueeze(0).to(device)
    
    # Run detection
    with torch.no_grad():
        prediction = detection_model(img_tensor)[0]
    
    boxes = prediction['boxes']
    scores = prediction['scores']
    
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
            
            detected_seeds.append({
                'box': (x1_orig, y1_orig, x2_orig, y2_orig),
                'detection_confidence': float(score)
            })
    
    return detected_seeds, (orig_h, orig_w)


def classify_seeds(rgb_img: np.ndarray, detected_seeds: List[Dict]) -> List[Dict]:
    """Classify each detected seed as Good or Bad"""
    classified_results = []
    
    for seed_data in detected_seeds:
        x1, y1, x2, y2 = seed_data['box']
        
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
        
        classified_results.append({
            'box': seed_data['box'],
            'detection_confidence': seed_data['detection_confidence'],
            'classification_probability': float(prob),
            'quality': label
        })
    
    return classified_results


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "Seed Quality Detection API",
        "models_loaded": detection_model is not None and classification_model is not None,
        "device": str(device)
    }


@app.post("/api/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """
    Main endpoint: Upload an image and get seed detection + classification results
    
    Returns:
    - bounding_boxes: List of detected seeds with coordinates and quality
    - statistics: Overall quality metrics
    - image_dimensions: Original image size for frontend scaling
    """
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read and process image
        contents = await file.read()
        rgb_img = process_uploaded_image(contents)
        
        # Step 1: Detect seeds
        detected_seeds, (img_height, img_width) = detect_seeds(rgb_img)
        
        if len(detected_seeds) == 0:
            return JSONResponse(content={
                "success": True,
                "message": "No seeds detected in the image",
                "total_seeds": 0,
                "bounding_boxes": [],
                "statistics": {
                    "good_seeds": 0,
                    "bad_seeds": 0,
                    "good_percentage": 0.0,
                    "bad_percentage": 0.0
                },
                "image_dimensions": {
                    "width": img_width,
                    "height": img_height
                }
            })
        
        # Step 2: Classify seeds
        classified_results = classify_seeds(rgb_img, detected_seeds)
        
        # Step 3: Calculate statistics
        good_count = sum(1 for s in classified_results if s['quality'] == 'Good')
        bad_count = sum(1 for s in classified_results if s['quality'] == 'Bad')
        total_count = len(classified_results)
        
        # Format bounding boxes for frontend
        bounding_boxes = []
        for idx, seed in enumerate(classified_results):
            x1, y1, x2, y2 = seed['box']
            bounding_boxes.append({
                "id": idx,
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "width": x2 - x1,
                "height": y2 - y1,
                "quality": seed['quality'],
                "detection_confidence": round(seed['detection_confidence'], 4),
                "classification_probability": round(seed['classification_probability'], 4),
                "color": "#FF0000" if seed['quality'] == 'Bad' else "#00FF00"  # Red or Green
            })
        
        response_data = {
            "success": True,
            "total_seeds": total_count,
            "bounding_boxes": bounding_boxes,
            "statistics": {
                "good_seeds": good_count,
                "bad_seeds": bad_count,
                "good_percentage": round((good_count / total_count * 100), 2) if total_count > 0 else 0,
                "bad_percentage": round((bad_count / total_count * 100), 2) if total_count > 0 else 0
            },
            "image_dimensions": {
                "width": img_width,
                "height": img_height
            },
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
        "device": str(device)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
