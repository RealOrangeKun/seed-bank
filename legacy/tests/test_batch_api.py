#!/usr/bin/env python3
import requests
import json
import sys
import os
from pathlib import Path

# Get project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

API_URL = "http://localhost:8000"
TEST_IMAGES_DIR = os.path.join(PROJECT_ROOT, "data/test-images/maize-test")

def test_batch_analysis():
    """Test batch analysis endpoint with multiple images"""
    print(f"Testing batch analysis with images from {TEST_IMAGES_DIR}...")
    
    # Get all image files
    image_files = list(Path(TEST_IMAGES_DIR).glob("*.png")) + \
                  list(Path(TEST_IMAGES_DIR).glob("*.jpg")) + \
                  list(Path(TEST_IMAGES_DIR).glob("*.jpeg"))
    
    # Take first 2 images for testing
    image_files = image_files[:2]
    
    if not image_files:
        print("No images found in test directory!")
        return False
    
    print(f"Found {len(image_files)} images to process")
    
    # Prepare files for upload
    files = []
    for img_path in image_files:
        files.append(
            ('files', (img_path.name, open(img_path, 'rb'), 'image/png'))
        )
    
    try:
        # Send batch request
        print(f"\nSending batch request to {API_URL}/api/analyze-batch...")
        response = requests.post(f"{API_URL}/api/analyze-batch", files=files)
        
        # Close file handles
        for _, (_, f, _) in files:
            f.close()
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n{'='*70}")
            print(f"✓ Batch Analysis Successful!")
            print(f"{'='*70}")
            print(f"Total images processed: {data['total_images']}")
            print(f"Total seeds detected (all images): {data['total_seeds_all_images']}")
            print(f"\nOverall Statistics:")
            print(f"  Good seeds: {data['overall_statistics']['good_seeds']} ({data['overall_statistics']['good_percentage']}%)")
            print(f"  Bad seeds: {data['overall_statistics']['bad_seeds']} ({data['overall_statistics']['bad_percentage']}%)")
            
            print(f"\n{'-'*70}")
            print(f"Individual Image Results:")
            print(f"{'-'*70}")
            
            for idx, result in enumerate(data['results'], 1):
                print(f"\n{idx}. {result['filename']}")
                print(f"   Seeds detected: {result['total_seeds']}")
                print(f"   Good: {result['statistics']['good_seeds']} ({result['statistics']['good_percentage']}%)")
                print(f"   Bad: {result['statistics']['bad_seeds']} ({result['statistics']['bad_percentage']}%)")
                print(f"   Dimensions: {result['image_dimensions']['width']}x{result['image_dimensions']['height']}")
                
                if result['bounding_boxes']:
                    print(f"   First seed: {result['bounding_boxes'][0]['quality']} "
                          f"(conf: {result['bounding_boxes'][0]['detection_confidence']:.3f})")
            
            print(f"\n{'='*70}\n")
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API. Is the server running?")
        return False
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        # First check health
        response = requests.get(f"{API_URL}/")
        if response.status_code == 200:
            print("✓ API is running")
            test_batch_analysis()
        else:
            print("API health check failed!")
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
