#!/usr/bin/env python3
import requests
import json

API_URL = "http://localhost:8000"

# Test single image with new metrics
print("Testing new confidence metrics...\n")

with open("data/test-images/maize-test/image.png", "rb") as f:
    files = {"file": ("image.png", f, "image/png")}
    response = requests.post(f"{API_URL}/api/analyze", files=files)

if response.status_code == 200:
    data = response.json()
    print("=" * 70)
    print("✓ API Response with New Confidence Metrics")
    print("=" * 70)
    print(f'Total seeds: {data["total_seeds"]}')

    print(f'\n{"First Seed Details":^70}')
    print("-" * 70)
    seed = data["bounding_boxes"][0]
    print(f'  Quality: {seed["quality"]}')
    print(f'  Good Percentage: {seed["good_percentage"]}%')
    print(f'  Bad Percentage: {seed["bad_percentage"]}%')
    print(f'  Classification Confidence: {seed["classification_confidence"]}%')
    print(f'  Raw Probability: {seed["raw_probability"]}')
    print(f'  Detection Confidence: {seed["detection_confidence"]}')
    print(f"\n  Physical Metrics:")
    print(f'    Area: {seed["area"]} px²')
    print(f'    Dimensions: {seed["width"]}×{seed["height"]} px')
    print(f'    Aspect Ratio: {seed["aspect_ratio"]}')
    print(f'    Centroid: ({seed["centroid"]["x"]}, {seed["centroid"]["y"]})')

    print(f'\n{"Confidence Score Examples":^70}')
    print("-" * 70)

    # Example: Very Good seed (low probability, far from threshold)
    good_seeds = [s for s in data["bounding_boxes"] if s["quality"] == "Good"]
    if good_seeds:
        seed = min(good_seeds, key=lambda x: x["raw_probability"])
        print(f"  Very Good Seed (far from threshold 0.9):")
        print(
            f'    Raw prob: {seed["raw_probability"]} → Confidence: {seed["classification_confidence"]}%'
        )
        print(f'    Good: {seed["good_percentage"]}% | Bad: {seed["bad_percentage"]}%')

    # Example: Borderline Good seed (close to threshold)
    borderline_good = [s for s in good_seeds if 0.7 < s["raw_probability"] < 0.9]
    if borderline_good:
        seed = max(borderline_good, key=lambda x: x["raw_probability"])
        print(f"\n  Borderline Good Seed (close to threshold):")
        print(
            f'    Raw prob: {seed["raw_probability"]} → Confidence: {seed["classification_confidence"]}%'
        )
        print(f'    Good: {seed["good_percentage"]}% | Bad: {seed["bad_percentage"]}%')

    # Example: Very Bad seed (high probability, far from threshold)
    bad_seeds = [s for s in data["bounding_boxes"] if s["quality"] == "Bad"]
    if bad_seeds:
        seed = max(bad_seeds, key=lambda x: x["raw_probability"])
        print(f"\n  Very Bad Seed (far from threshold):")
        print(
            f'    Raw prob: {seed["raw_probability"]} → Confidence: {seed["classification_confidence"]}%'
        )
        print(f'    Good: {seed["good_percentage"]}% | Bad: {seed["bad_percentage"]}%')

    # Example: Borderline Bad seed
    borderline_bad = [s for s in bad_seeds if 0.9 < s["raw_probability"] < 0.95]
    if borderline_bad:
        seed = min(borderline_bad, key=lambda x: x["raw_probability"])
        print(f"\n  Borderline Bad Seed (close to threshold):")
        print(
            f'    Raw prob: {seed["raw_probability"]} → Confidence: {seed["classification_confidence"]}%'
        )
        print(f'    Good: {seed["good_percentage"]}% | Bad: {seed["bad_percentage"]}%')

    # Statistics
    print(f'\n{"Confidence Distribution":^70}')
    print("-" * 70)
    avg_good_conf = (
        sum(s["classification_confidence"] for s in good_seeds) / len(good_seeds)
        if good_seeds
        else 0
    )
    avg_bad_conf = (
        sum(s["classification_confidence"] for s in bad_seeds) / len(bad_seeds)
        if bad_seeds
        else 0
    )
    print(f"  Average Good Seeds Confidence: {avg_good_conf:.2f}%")
    print(f"  Average Bad Seeds Confidence: {avg_bad_conf:.2f}%")

    print("=" * 70)
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)
