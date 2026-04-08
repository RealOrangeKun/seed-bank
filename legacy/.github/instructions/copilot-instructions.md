# Copilot Instructions for Seed Bank

## Project Overview
Seed Quality Detection API using a two-stage ML pipeline: **Faster R-CNN** (object detection) → **ResNet50** (binary classification: Good/Bad). Built with FastAPI + PostgreSQL, designed for agricultural quality control.

## Architecture

### ML Pipeline Flow
1. Image upload → `process_uploaded_image()` → RGB numpy array
2. `detect_seeds()` → Faster R-CNN detects seed bounding boxes (confidence >90%)
3. `classify_seeds()` → ResNet50 classifies each crop as Good/Bad (threshold 0.9)
4. Results persisted to PostgreSQL via SQLAlchemy models

### Key Components
- [main.py](../main.py) - FastAPI app with all endpoints and ML inference logic (monolith)
- [app/models.py](../app/models.py) - SQLAlchemy models: `User`, `ScanBatch`, `ScanImage`, `SeedDetection`
- [app/crud.py](../app/crud.py) - Database operations, guest user management via device fingerprinting
- [app/database.py](../app/database.py) - DB connection using `psycopg3` (not psycopg2)

### Database Schema
```
User (guest via device_fingerprint) → ScanBatch → ScanImage → SeedDetection
```
- Bounding boxes stored as **normalized coordinates** (0.0-1.0) for resolution independence
- Processing status tracked via `ProcessingStatus` enum

## Development Setup

### Quick Start (Docker - recommended)
```bash
docker-compose up -d postgres   # Start PostgreSQL first
alembic upgrade head            # Run migrations
python main.py                  # Start API at :8000
```

### Full Stack
```bash
docker-compose up               # API(:8000) + Frontend(:8080) + Adminer(:8081) + Postgres
```

### Local Development
```bash
pip install -r requirements.txt
# Requires models/ directory with .pth files (not in git)
DATABASE_URL=postgresql://seedbank:seedbank_dev_password@localhost:5432/seedbank_db
```

## API Endpoints Pattern
| Endpoint | Purpose |
|----------|---------|
| `POST /api/analyze` | Single image analysis |
| `POST /api/analyze-batch` | Multi-image batch processing |
| `POST /api/analyze/fast` & `/api/analyze-batch/fast` | Speed-optimized variants |
| `GET /api/batches`, `/api/batches/{id}` | Retrieve scan history |
| `GET /api/stats` | User statistics |

## Code Conventions

### Model Loading
Models load on FastAPI startup event (`@app.on_event("startup")`). They're stored as globals: `detection_model`, `classification_model`, `device`.

### Image Processing
- Use `albumentations` for detection preprocessing (224x224, normalized)
- Use `torchvision.transforms` for classification
- All inference wrapped in `torch.no_grad()` context

### Database Patterns
- Use `Depends(get_db)` for session injection
- Guest users identified by device fingerprint hash from User-Agent + IP
- Always use `psycopg3` driver syntax: `postgresql+psycopg://`

### Response Structure
Endpoints return consistent structure with:
- `bounding_boxes[]` with normalized + absolute coordinates
- `statistics` with aggregated counts
- `batch_id` for tracking

## Testing
```bash
python tests/test_api.py        # Integration tests (requires running server)
python tests/test_batch_api.py  # Batch endpoint tests
```
Tests use test images from `data/test-images/maize-test/`.

## Migrations
```bash
alembic revision --autogenerate -m "description"  # Create migration
alembic upgrade head                               # Apply migrations
alembic downgrade -1                               # Rollback one
```
Migrations are in `alembic/versions/`. Schema defined code-first in `app/models.py`.

## GPU Support
- Docker uses NVIDIA CUDA 11.8 base image
- Falls back to CPU if no GPU available
- Check device: `GET /` returns `device` field
