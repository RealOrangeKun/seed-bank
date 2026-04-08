#!/usr/bin/env python3
"""
Automated patch script to integrate multi-model system into main.py
This script updates main.py to use the new ModelManager and detection pipeline.
"""

import re

def patch_main_py():
    """Apply all necessary patches to main.py"""
    
    with open('main.py', 'r') as f:
        content = f.read()
    
    original_content = content
    
    print("Patching main.py for multi-model support...")
    
    # 1. Add import for detection pipeline
    if 'from app.ml.detection_pipeline import' not in content:
        content = content.replace(
            'from app.ml.model_manager import ModelManager',
            'from app.ml.model_manager import ModelManager\nfrom app.ml.detection_pipeline import detect_seeds_multi, classify_seeds_multi'
        )
        print("✓ Added detection_pipeline imports")
    
    # 2. Replace load_models function
    old_load_models = re.search(
        r'@app\.on_event\("startup"\)\s*\nasync def load_models\(\):.*?print\("✓ Classification model loaded successfully"\)',
        content,
        re.DOTALL
    )
    
    if old_load_models:
        new_load_models = '''@app.on_event("startup")
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
        
        print("\\n" + "="*50)
        print("MODEL CONFIGURATION")
        print("="*50)
        config = model_manager.get_config_summary()
        print(f"Detection: {config['detection_model']['name']} (v{config['detection_model']['version']})")
        print(f"Quality Models:")
        for seed_type, model_info in config['quality_models'].items():
            print(f"  - {seed_type}: {model_info['name']} (threshold={model_info['threshold']})")
        print("="*50 + "\\n")
        
    finally:
        db.close()'''
        
        content = content.replace(old_load_models.group(0), new_load_models)
        print("✓ Replaced load_models function")
    
    # 3. Replace detect_seeds function
    old_detect = re.search(
        r'def detect_seeds\(rgb_img: np\.ndarray\) -> tuple:.*?return detected_seeds, \(orig_h, orig_w\)',
        content,
        re.DOTALL
    )
    
    if old_detect:
        new_detect = '''def detect_seeds(rgb_img: np.ndarray) -> tuple:
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
    )'''
        
        content = content.replace(old_detect.group(0), new_detect)
        print("✓ Replaced detect_seeds function")
    
    # 4. Replace classify_seeds function  
    old_classify = re.search(
        r'def classify_seeds\(rgb_img: np\.ndarray, detected_seeds: List\[Dict\]\) -> List\[Dict\]:.*?return classified_results',
        content,
        re.DOTALL
    )
    
    if old_classify:
        new_classify = '''def classify_seeds(rgb_img: np.ndarray, detected_seeds: List[Dict]) -> List[Dict]:
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
    )'''
        
        content = content.replace(old_classify.group(0), new_classify)
        print("✓ Replaced classify_seeds function")
    
    # 5. Update root endpoint
    content = content.replace(
        '"models_loaded": detection_model is not None\n        and classification_model is not None,',
        '"models_loaded": model_manager is not None,'
    )
    print("✓ Updated root endpoint")
    
    # 6. Add seed_type_id to SeedDetection creation (in analyze_image)
    content = re.sub(
        r'(SeedDetection\(\s*batch_id=scan_batch\.id,\s*image_id=scan_image\.id,)',
        r'\1\n                seed_type_id=seed_data["seed_type_id"],',
        content
    )
    print("✓ Added seed_type_id to SeedDetection (analyze_image)")
    
    # 7. Add seed_type_id to SeedDetection creation (in analyze_batch)
    # This is already handled by the regex above
    
    # 8. Add seed_type to bounding_boxes (analyze_image)
    content = re.sub(
        r'(bounding_boxes\.append\(\s*\{\s*"id": idx,)',
        r'\1\n                    "seed_type": seed["seed_type_name"],',
        content,
        count=1  # Only first occurrence (analyze_image)
    )
    print("✓ Added seed_type to bounding_boxes (analyze_image)")
    
    # 9. Add seed_type to bounding_boxes (analyze_batch)
    content = re.sub(
        r'(bounding_boxes\.append\(\s*\{\s*"id": idx,)',
        r'\1\n                            "seed_type": seed["seed_type_name"],',
        content
    )
    print("✓ Added seed_type to bounding_boxes (analyze_batch)")
    
    # 10. Add new endpoint for model configuration
    new_endpoint = '''

@app.get("/api/models/config")
async def get_models_config():
    """Get active model configurations from database"""
    if model_manager is None:
        raise HTTPException(status_code=503, detail="Models not loaded")
    
    return model_manager.get_config_summary()
'''
    
    # Insert after get_config endpoint
    content = re.sub(
        r'(@app\.get\("/api/config"\).*?}\s*\n)',
        r'\1' + new_endpoint,
        content,
        flags=re.DOTALL
    )
    print("✓ Added /api/models/config endpoint")
    
    # Write back
    if content != original_content:
        with open('main.py', 'w') as f:
            f.write(content)
        print("\n✅ Successfully patched main.py!")
        print("Restart the server to see the changes.")
        return True
    else:
        print("\n⚠️  No changes made - file may already be patched")
        return False

if __name__ == "__main__":
    patch_main_py()
