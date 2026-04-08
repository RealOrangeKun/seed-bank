#!/usr/bin/env python3
import requests
import json
import sys
import os

# Get project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

API_URL = "http://localhost:8000"
IMAGE_PATH = os.path.join(PROJECT_ROOT, "data/test-images/maize-test/image.png")

def test_health():
    """Test health check endpoint"""
    print("Testing health check...")
    response = requests.get(f"{API_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    return response.status_code == 200

def test_analyze():
    """Test image analysis endpoint"""
    print(f"Testing image analysis with {os.path.basename(IMAGE_PATH)}...")
    
    with open(IMAGE_PATH, 'rb') as f:
        files = {'file': (os.path.basename(IMAGE_PATH), f, 'image/png')}
        response = requests.post(f"{API_URL}/api/analyze", files=files)
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n{'='*60}")
        print(f"✓ Analysis successful!")
        print(f"{'='*60}")
        print(f"Total seeds detected: {data['total_seeds']}")
        print(f"Good seeds: {data['statistics']['good_seeds']} ({data['statistics']['good_percentage']}%)")
        print(f"Bad seeds: {data['statistics']['bad_seeds']} ({data['statistics']['bad_percentage']}%)")
        print(f"\nImage dimensions: {data['image_dimensions']['width']}x{data['image_dimensions']['height']}")
        print(f"\nFirst 3 bounding boxes:")
        for i, box in enumerate(data['bounding_boxes'][:3]):
            print(f"  Seed {i+1}: [{box['x1']}, {box['y1']}, {box['x2']}, {box['y2']}] - {box['quality']} (conf: {box['detection_confidence']:.3f})")
        print(f"{'='*60}\n")
        return True
    else:
        print(f"Error: {response.text}")
        return False

if __name__ == "__main__":
    try:
        if test_health():
            test_analyze()
        else:
            print("Health check failed!")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API. Is the server running?")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
