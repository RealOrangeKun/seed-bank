# Enhanced Seed Quality Metrics

## Overview
The API now returns comprehensive per-seed metrics including exponentially-weighted confidence scores and physical measurements.

## New Metrics

### 1. Confidence Scoring (Exponential Weighting)
- **Formula**: `confidence = (1 - e^(-k × distance)) × 100%`
- **k-value**: 8.0 (amplifies early differences from threshold)
- **Threshold**: 0.9

#### Confidence Components:
- **good_percentage**: Percentage confidence that seed is good quality (0-100%)
- **bad_percentage**: Percentage confidence that seed is bad quality (0-100%)
- **classification_confidence**: Overall confidence in the classification (0-100%)
- **raw_probability**: Original model probability (0-1)

#### Examples:
```
Very Good Seed (prob=0.0193, far from threshold):
  - Confidence: 99.91%
  - Good: 98.07% | Bad: 1.93%

Borderline Good (prob=0.8902, close to threshold):
  - Confidence: 7.51%
  - Good: 10.98% | Bad: 89.02%

Very Bad Seed (prob=1.0, far from threshold):
  - Confidence: 55.06%
  - Good: 0.0% | Bad: 100.0%

Borderline Bad (prob=0.9119, close to threshold):
  - Confidence: 9.07%
  - Good: 8.81% | Bad: 91.19%
```

### 2. Physical Metrics
- **area**: Bounding box area in pixels² (width × height)
- **width**: Seed width in pixels
- **height**: Seed height in pixels
- **aspect_ratio**: Width/height ratio (shape indicator)
- **centroid**: Center point coordinates (x, y)

### 3. Detection Metrics
- **detection_confidence**: Faster R-CNN confidence score (0-1)
- **x1, y1, x2, y2**: Bounding box coordinates

## API Response Format

### Single Image Endpoint: `/api/analyze`
```json
{
  "bounding_boxes": [
    {
      "x1": 811, "y1": 587, "x2": 877, "y2": 672,
      "width": 66,
      "height": 85,
      "area": 5610,
      "aspect_ratio": 0.78,
      "centroid": [844, 629],
      "quality": "Good",
      "detection_confidence": 0.9999,
      "good_percentage": 10.98,
      "bad_percentage": 89.02,
      "classification_confidence": 7.51,
      "raw_probability": 0.8902,
      "color": "#00FF00"
    }
  ],
  "statistics": {
    "total_seeds": 95,
    "good_seeds": 52,
    "bad_seeds": 43,
    "good_percentage": 54.74,
    "bad_percentage": 45.26
  },
  "image_dimensions": {"width": 2592, "height": 1944}
}
```

### Batch Endpoint: `/api/analyze-batch`
```json
{
  "results": [
    {
      "filename": "image.png",
      "bounding_boxes": [...],
      "statistics": {...}
    }
  ],
  "overall_statistics": {
    "total_images": 2,
    "total_seeds": 186,
    "total_good": 86,
    "total_bad": 100,
    "overall_good_percentage": 46.24,
    "overall_bad_percentage": 53.76
  }
}
```

## Implementation Details

### calculate_confidence_score() Function
```python
def calculate_confidence_score(prob: float, threshold: float = 0.9, k: float = 8.0):
    """
    Calculate confidence score using exponential weighting.
    Early differences from threshold are amplified more strongly.
    
    Args:
        prob: Classification probability (0-1)
        threshold: Decision boundary (default 0.9)
        k: Exponential coefficient (default 8.0)
        
    Returns:
        dict with good_percentage, bad_percentage, 
        classification_confidence, raw_probability
    """
```

### classify_seeds() Enhancement
Added physical metrics calculation for each detected seed:
- Bounding box dimensions (width, height, area)
- Aspect ratio (shape descriptor)
- Centroid coordinates (position tracking)

## Testing Results

### Average Confidence Distribution:
- **Good Seeds**: 88.78% average confidence
- **Bad Seeds**: 43.55% average confidence

This shows the model is more confident about good seeds than bad seeds, which aligns with typical classification behavior.

## Benefits

1. **Confidence Interpretation**: Users can see how certain the model is about each classification
2. **Quality Assessment**: Borderline cases are identified with low confidence scores
3. **Physical Analysis**: Seed size and shape metrics enable additional quality checks
4. **Position Tracking**: Centroid coordinates allow spatial analysis of seed distribution
5. **Exponential Scaling**: Early differences from threshold are weighted more heavily, making subtle variations more apparent

## Next Steps

Consider adding:
- Color analysis (mean RGB/HSV values)
- Texture features (standard deviation, entropy)
- Shape irregularity scores
- Seed-to-seed distance metrics
- Clustering analysis for spatial patterns
