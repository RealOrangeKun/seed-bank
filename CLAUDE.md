# CLAUDE.md

Guidance for Claude Code (and humans) working in this repository.

## What this is

**Seed Bank** is an AI-powered seed quality detection system for agricultural quality
control. It runs a **two-stage ML pipeline** over uploaded images:

1. **Detection** — a Faster R-CNN (ResNet50-FPN) with **3 classes** (`0=background`,
   `1=coffee`, `2=maize`) locates individual seeds and identifies their type.
2. **Quality classification** — a per-seed-type ResNet18 (with a CBAM attention block and
   hybrid GAP+GMP pooling) classifies each detected seed crop as **Good** or **Bad**.

Results are persisted to PostgreSQL and exposed through a FastAPI REST API. A vanilla-JS +
Tailwind frontend consumes the API (upload, bounding-box overlay, history, stats, PDF report).

## Architecture

```
Image upload
  → process_uploaded_image()          # bytes → RGB numpy (OpenCV)
  → detect_seeds_multi()              # Faster R-CNN, 3-class, NMS, threshold filter
  → classify_seeds_multi()            # routes each crop to coffee/maize quality model
  → persist (User → ScanBatch → ScanImage → SeedDetection)
  → JSON response (boxes + statistics + image_dimensions)
```

### Key files
- `main.py` — **monolith** FastAPI app: all routes, request/response shaping, persistence,
  and thin wrappers (`detect_seeds`, `classify_seeds`) over the ML pipeline. ~1650 lines.
- `app/ml/model_manager.py` — `ModelManager` loads all **active** models from the
  `ai_models` DB table at startup; maps `seed_type_id → quality model + threshold`.
- `app/ml/detection_pipeline.py` — `detect_seeds_multi`, `classify_seeds_multi`,
  `calculate_confidence_from_logits` (the **real** confidence math — BCEWithLogits based).
- `app/ml/model_builders.py` — architecture builders for the 3 models.
- `app/ml/cbam.py` — CBAM attention module used by the quality models.
- `app/models.py` — SQLAlchemy models: `SeedCatalog`, `AIModel`, `User`, `ScanBatch`,
  `ScanImage`, `SeedDetection` (+ `ProcessingStatus`, `QualityLabel` enums).
- `app/crud.py` — guest-user management (device fingerprinting), batch/detection/stats queries.
- `app/database.py` — engine/session; normalizes `postgresql://` → `postgresql+psycopg://`.
- `alembic/versions/` — code-first migrations; `003` seeds `seed_catalog` + `ai_models`.
- `frontend/` — static SPA (`index.html`, `script.js`, Tailwind `style.css`). API base is
  hardcoded in `script.js` (`API_URL`).

### Data model
```
User (guest via device_fingerprint)
  └─ ScanBatch (one API call; status, timings, aggregate stats)
       ├─ ScanImage (one uploaded image; storage_path, dimensions)
       └─ SeedDetection (one seed; quality, confidences, normalized bbox, physical metrics)
SeedCatalog (maize, coffee)  ─┐
AIModel (detection + per-type quality, is_active, threshold) ─┘
```
Bounding boxes are stored **normalized 0.0–1.0** (`box_*_norm`) for resolution independence
and future object-storage migration. API responses return **absolute pixel** coords.

## Models / weights

Weights are **not in git** (`*.pth` is gitignored) and are large (~260 MB total). They must
exist at the paths recorded in the `ai_models` table:
- `models/FasterRCNN_ResNet50_Final_Combined.pth` (detection, 3-class)
- `models/ResNet18_COFFEE_BEANS_V3.pth` (coffee quality)
- `models/ResNet18_maize_Transfer_learning_wCBAM&GMP_smallerStride_Hybrid_v4.pth` (maize quality)

`ModelManager` raises `FileNotFoundError` at startup if any active model file is missing, so
**the app will not start without the weights present**. Tests mock the model manager so they
do not require weights (see Testing).

## Commands

This environment uses a local venv at `.venv` (CPU torch). Postgres for local dev runs in a
container on **host port 5433** (5432 is often taken by another service on this machine).

```bash
# --- environment ---
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt          # full (CUDA) deps
# CPU-only torch (this machine): install torch/torchvision from the cpu index first,
# then `grep -viE '^(nvidia-|torch==|torchvision==|triton==)' requirements.txt | pip install -r /dev/stdin`

# --- database (local dev on 5433) ---
docker run -d --name seed_bank_postgres \
  -e POSTGRES_USER=seedbank -e POSTGRES_PASSWORD=seedbank_dev_password -e POSTGRES_DB=seedbank_db \
  -p 5433:5432 postgres:17-alpine
export DATABASE_URL="postgresql+psycopg://seedbank:seedbank_dev_password@localhost:5433/seedbank_db"
.venv/bin/alembic upgrade head                     # apply migrations + seed data
.venv/bin/alembic downgrade -1                      # roll back one
.venv/bin/alembic revision --autogenerate -m "msg" # new migration

# --- run the API (requires model weights present) ---
DATABASE_URL=... .venv/bin/python main.py           # serves on :8000
# or: .venv/bin/uvicorn main:app --reload --port 8000

# --- tests ---
.venv/bin/python -m pytest                          # unit + mocked-model API + DB integration
.venv/bin/python -m pytest -m "not integration"     # skip DB-backed tests
# Legacy manual scripts (need a running server + real weights):
.venv/bin/python tests/test_api.py
.venv/bin/python tests/test_batch_api.py

# --- full stack via compose (note port clashes: 5432, 8080 may be taken) ---
docker compose up                                   # api:8000 web:8080 adminer:8081 postgres:5432
```

## API surface (all under `/api` except `/`)

| Method | Path | Notes |
|---|---|---|
| GET | `/` | health: `models_loaded`, `device` |
| POST | `/api/analyze` | single image (accurate, local models) — persists |
| POST | `/api/analyze-batch` | multi-image (accurate) — persists |
| POST | `/api/analyze/fast` | single image via **Roboflow** detection + local classify — **does NOT persist** |
| POST | `/api/analyze-batch/fast` | multi-image fast — persists |
| GET | `/api/config` | thresholds + device |
| GET | `/api/models/config` | active model config summary |
| GET | `/api/batches` | paginated history (per device fingerprint) |
| GET | `/api/batches/{id}` | batch detail + images |
| GET | `/api/batches/{id}/detections` | detections, filterable by image/quality |
| GET | `/api/stats` | aggregated user statistics |
| GET | `/api/images/{batch_id}/by-id/{image_id}` | serve image (ownership-checked) |
| GET | `/api/images/{batch_id}/{filename}` | serve image by filename (path-traversal guarded) |

Users are anonymous "guests" keyed by a **device fingerprint** = `md5(user-agent + client-ip)`.
There is no auth; history/ownership is scoped by that fingerprint.

## Conventions
- Models load once on FastAPI `startup` into the module-global `model_manager`.
- All inference runs under `torch.no_grad()`.
- DB sessions via `Depends(get_db)`; always use the `postgresql+psycopg://` driver.
- Endpoints return a consistent shape: `success`, `bounding_boxes[]` (absolute px),
  `statistics`, `image_dimensions`, and `batch_id` for persisted calls.
- Quality decision is logit-threshold based: `logit >= threshold ⇒ Good` (per-type threshold
  from `ai_models.default_threshold`; e.g. maize=5.0, coffee=0.0).

## Gotchas / known rough edges
- `tests/*` are **manual scripts**, not pytest, and require a running server + weights.
  `tests/test_confidence_metrics.py` references a `raw_probability` field the API no longer returns.
- `ENHANCED_METRICS.md` documents an old exponential confidence formula / `raw_probability`;
  the live code uses `calculate_confidence_from_logits` (sigmoid + distance-from-threshold).
- `TESTING_PHASE_1_2.md` references a `guests` table (now `users`) and a stale absolute path.
- `/api/analyze/fast` ships a **hardcoded Roboflow API key** in `main.py` — should be an env var.
- Several response dicts contain a duplicated `"seed_type"` key (harmless but sloppy).
