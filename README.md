# 🌱 Seed Bank — Seed Quality Intelligence

AI-powered seed quality assessment with a **two-stage deep-learning pipeline**, a FastAPI
backend, PostgreSQL persistence, and a polished vanilla-JS + Tailwind frontend.

## 🎯 Overview

1. **Detection** — a Faster R-CNN (ResNet50-FPN) with **3 classes** (`background`, `coffee`,
   `maize`) locates individual seeds and identifies their type.
2. **Quality classification** — a per-seed-type **ResNet18 with a CBAM attention block and
   hybrid GAP+GMP pooling** classifies each detected seed crop as **Good** or **Bad** via a
   logit threshold loaded per seed type from the database.

Results are persisted (`User → ScanBatch → ScanImage → SeedDetection`) and exposed through a
REST API. The frontend adds bounding-box overlays, history, an analytics dashboard, batch
comparison, data export, sharing, and PDF/CSV/JSON reports.

> Models are configured **in the database** (`ai_models` table), not hardcoded — the app loads
> all active models at startup via `ModelManager`. See [CLAUDE.md](CLAUDE.md) for the full
> architecture and [TESTING.md](TESTING.md) for the test setup.

## ✨ Features

- 🔍 Multi-seed detection (**maize + coffee**) with per-type quality classification
- 📊 Analytics dashboard (quality trend, type split, size & confidence histograms)
- 🆚 Side-by-side **batch comparison**
- 🗂️ Scan **history** with search / sort / date filters, delete & bulk delete
- 📤 **Export** detections as CSV / JSON; download **annotated** images (boxes burned in)
- 🔗 **Shareable** read-only report links
- 🌓 Dark mode, toasts, keyboard shortcuts, settings panel
- ⚡ Optional **fast mode** (Roboflow detection + local classification)
- 🩺 `/health` & `/readiness` probes, structured request logging, rate limiting

## 📁 Project structure

```
seed-bank/
├── main.py                 # FastAPI app: routes, request/response shaping, persistence
├── app/
│   ├── database.py         # engine/session (psycopg3)
│   ├── models.py           # SQLAlchemy models + enums
│   ├── crud.py             # user/batch/detection/stats/analytics/export/share queries
│   ├── observability.py    # structured logging + request-id/timing middleware
│   ├── limits.py           # rate limiter + upload guards
│   └── ml/
│       ├── model_manager.py    # loads active models from the DB
│       ├── model_builders.py   # detection + per-type quality architectures
│       ├── detection_pipeline.py  # detect_seeds_multi / classify_seeds_multi
│       └── cbam.py             # CBAM attention module
├── alembic/                # migrations (004 = latest); migration 003 seeds models/catalog
├── frontend/               # static SPA (index.html, script.js, dashboard.js, Tailwind)
├── tests/                  # pytest: unit + mocked-model API + DB integration
├── docker-compose.yml      # postgres + adminer + api + web
└── models/                 # *.pth weights (NOT in git)
```

## 🚀 Quick start

### 1. Database (Docker)

```bash
# 5432 is often taken locally; this repo's docs use 5433 for dev.
docker run -d --name seed_bank_postgres \
  -e POSTGRES_USER=seedbank -e POSTGRES_PASSWORD=seedbank_dev_password -e POSTGRES_DB=seedbank_db \
  -p 5433:5432 postgres:17-alpine
export DATABASE_URL="postgresql+psycopg://seedbank:seedbank_dev_password@localhost:5433/seedbank_db"
```

### 2. Python env + migrations

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt        # GPU build; for CPU see CLAUDE.md
.venv/bin/alembic upgrade head                   # creates tables + seeds seed_catalog/ai_models
```

### 3. Model weights

Place the three weight files where the seeded `ai_models` rows expect them:

- `models/FasterRCNN_ResNet50_Final_Combined.pth` (detection, 3-class)
- `models/ResNet18_COFFEE_BEANS_V3.pth` (coffee quality)
- `models/ResNet18_maize_Transfer_learning_wCBAM&GMP_smallerStride_Hybrid_v4.pth` (maize quality)

> Weights are gitignored and not distributed here. `ModelManager` raises at startup if an
> active model file is missing, so the API will not start without them.

### 4. Run

```bash
DATABASE_URL=... .venv/bin/python main.py        # API at http://localhost:8000
# Frontend: open frontend/index.html (or `python -m http.server` in ./frontend)
# Full stack: docker compose up   (ports configurable via *_HOST_PORT env vars)
```

Interactive API docs: **http://localhost:8000/docs**.

## 📡 API at a glance

| Group | Endpoints |
|---|---|
| **System** | `GET /`, `GET /health`, `GET /readiness`, `GET /api/config`, `GET /api/models/config` |
| **Analysis** | `POST /api/analyze`, `/api/analyze-batch`, `/api/analyze/fast`, `/api/analyze-batch/fast` |
| **History** | `GET /api/batches` (sort/filter), `GET /api/batches/{id}`, `…/detections`, `DELETE /api/batches/{id}`, `POST /api/batches/delete` |
| **Analytics** | `GET /api/stats`, `GET /api/analytics`, `POST /api/compare` |
| **Reports** | `…/export.csv`, `…/export.json`, `…/images/{image_id}/annotated.png`, `POST/DELETE …/share`, `GET /api/shared/{token}` |
| **Images** | `GET /api/images/{batch_id}/by-id/{image_id}`, `GET /api/images/{batch_id}/{filename}` |

Users are anonymous **guests** keyed by a device fingerprint (`md5(user-agent + client-ip)`);
history and ownership are scoped to that fingerprint. Analyze endpoints are rate-limited and
reject oversized / too-many uploads.

### Example

```bash
curl -X POST http://localhost:8000/api/analyze -F "file=@seeds.jpg" | jq '.statistics'
```

```json
{ "good_seeds": 52, "bad_seeds": 43, "good_percentage": 54.74, "bad_percentage": 45.26 }
```

See [ENHANCED_METRICS.md](ENHANCED_METRICS.md) for the per-seed response shape.

## 🧪 Testing

```bash
.venv/bin/python -m pytest                 # unit + mocked-model API + DB integration
.venv/bin/python -m pytest -m "not integration"
.venv/bin/ruff check .
```

Tests **mock the model manager**, so they run without GPU or weights. Details in
[TESTING.md](TESTING.md). CI runs ruff + pytest with a Postgres service on every push/PR.

## ⚙️ Configuration

Key environment variables (see [env.example](env.example)):

| Var | Purpose |
|---|---|
| `DATABASE_URL` | Postgres connection (psycopg3) |
| `CORS_ORIGINS` | comma-separated origins (`*` disables credentials) |
| `ROBOFLOW_API_KEY` / `ROBOFLOW_MODEL_ID` | enable fast mode (else those endpoints return 503) |
| `RATE_LIMIT_REQUESTS` / `RATE_LIMIT_WINDOW_S` | per-device rate limit |
| `MAX_UPLOAD_MB` / `MAX_BATCH_IMAGES` | upload guards |
| `LOG_LEVEL` | logging verbosity |

## 📄 License

Part of a graduation project.

## 🙏 Acknowledgments

PyTorch / torchvision, FastAPI, OpenCV, Chart.js.

---

**Made with 🌱 for agricultural quality control.**
