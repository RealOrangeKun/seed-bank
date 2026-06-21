# Enhanced Seed Quality Metrics

## Overview
Each detected seed carries per-seed confidence and physical metrics. This document reflects
the **current** implementation in `app/ml/detection_pipeline.py`
(`calculate_confidence_from_logits`).

> Historical note: an earlier version used a probability + exponential formula and exposed a
> `raw_probability` field. The quality models now use **BCEWithLogitsLoss**, so the API
> exposes raw **logits** instead. The fields below are authoritative.

## How quality is decided
The per-seed-type quality model outputs a single **logit**. The decision is a threshold on
that logit (per seed type, from `ai_models.default_threshold`):

```
logit >= threshold  ->  Good
logit <  threshold  ->  Bad
```
Defaults: maize threshold = 5.0, coffee threshold = 0.0.

## Confidence metrics (per seed)
Computed by `calculate_confidence_from_logits(logits, threshold)`:

- **good_percentage** / **bad_percentage** — complementary scores (sum to 100). Derived from
  the distance of the logit from the decision threshold, clamped so the chosen side is ≥ 50%.
- **classification_confidence** — `sigmoid(logit) * 100`, a probability-style display value.
- **raw_logits** — the raw model output (rounded), for transparency/debugging.

```python
{
  "good_percentage": 92.5,
  "bad_percentage": 7.5,
  "classification_confidence": 88.1,   # 100 * sigmoid(logit)
  "raw_logits": 7.1234
}
```

## Physical metrics (per seed)
- **area** — bounding-box area in px² (width × height)
- **width**, **height** — box dimensions in px
- **aspect_ratio** — width / height (shape descriptor)
- **centroid** — `{ "x": .., "y": .. }` center point

## Detection metrics (per seed)
- **detection_confidence** — Faster R-CNN score (0–1)
- **seed_type** — `maize` or `coffee` (from the 3-class detector)
- **x1, y1, x2, y2** — absolute pixel coordinates in the original image

## API response shape (`POST /api/analyze`)
```jsonc
{
  "success": true,
  "batch_id": 123,
  "total_seeds": 95,
  "bounding_boxes": [
    {
      "id": 0,
      "seed_type": "maize",
      "x1": 811, "y1": 587, "x2": 877, "y2": 672,
      "width": 66, "height": 85, "area": 5610,
      "aspect_ratio": 0.78,
      "centroid": { "x": 844, "y": 629 },
      "quality": "Good",
      "detection_confidence": 0.9999,
      "good_percentage": 92.5,
      "bad_percentage": 7.5,
      "classification_confidence": 88.1,
      "color": "#00FF00"
    }
  ],
  "statistics": { "good_seeds": 52, "bad_seeds": 43, "good_percentage": 54.74, "bad_percentage": 45.26 },
  "image_dimensions": { "width": 959, "height": 930 },
  "thresholds": { /* model_manager.get_config_summary() */ }
}
```

## Aggregate analytics
For cross-batch insight (totals, daily trend, seed-type split, size/confidence histograms)
see `GET /api/analytics`. Per-batch detection data can be exported via
`GET /api/batches/{id}/export.csv` and `.json`.

## Notes
- Bounding boxes are stored **normalized (0–1)** in the DB (`box_*_norm`) and returned as
  **absolute pixels** in API responses.
- `confidence_score` persisted on `seed_detections` is `classification_confidence / 100`.
