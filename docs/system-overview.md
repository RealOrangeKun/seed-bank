# Seed Bank — Complete System Overview

> **Audience & purpose.** This is the single, comprehensive source of truth for
> the Seed Bank system, written to be read cold by a new engineer **or** an AI
> agent. It explains what the product is, every component, how they fit together,
> the data and ML pipeline, all three clients (API, web, mobile), the
> infrastructure, and how to run and extend everything. When in doubt, this
> document is the map; the code is the territory. Deeper, narrower material lives
> in the sibling docs referenced at the end ([`docs/diagrams/`](./diagrams/),
> [`docs/adr/`](./adr/), [`docs/operations.md`](./operations.md),
> [`docs/revamp-status.md`](./revamp-status.md)).

Last updated: 2026-06-25. **Status: v1 — final.** This revision completes the
infrastructure, observability, and end-to-end tooling coverage; it is intended to
be exhaustive (every service, queue, image target, metric, dashboard, admin UI,
Make target, and external tool the project uses is documented here).

---

## 1. What Seed Bank is

Seed Bank is a **seed-quality intelligence platform**. A user photographs a
batch of seeds; the system **detects** each individual seed in the image and
**classifies** its quality (good vs. bad), then reports aggregate metrics
(seed count, good-rate, confidence distribution, per-seed-type breakdown).

It serves two very different audiences from one backend:

- **Farmers / end users** — the people checking seed quality in the field. They
  use the **web app** or the **mobile app**, in **Arabic or English**. Their
  journey is: sign in → photograph seeds → get an instant good/bad report →
  review history → optionally share a read-only report link.
- **AI developers & administrators** — the people who run the ML platform behind
  the product: registering model weights, promoting models through a lifecycle,
  splitting inference traffic for A/B tests, running offline evaluation
  experiments against labelled datasets, and managing users.

The platform is built around **full model traceability**: every individual seed
detection is linked to the inference run that produced it, which is linked to
the exact model version that ran, so any result can be traced back to the model
and weights that generated it.

---

## 2. High-level architecture

```
                        ┌──────────────────────────────────────────────┐
   Farmers / Devs        │                  CLIENTS                      │
   ───────────           │  Web app (React/Vite)   Mobile app (Expo/RN)  │
                         │  EN/AR + RTL            EN/AR + RTL, camera    │
                         └───────────────┬───────────────┬──────────────┘
                                         │  HTTPS / JSON  │  (+ multipart upload)
                                         ▼                ▼
                         ┌──────────────────────────────────────────────┐
                         │            FastAPI backend (async)            │
                         │  routers → services → repositories → ORM      │
                         │  auth · RBAC · rate-limit · RFC 9457 errors   │
                         └───┬─────────┬─────────┬─────────┬────────┬────┘
                             │         │         │         │        │
                   Postgres ◀┘  Redis ◀┘  MinIO ◀┘ ClickHouse│   MLflow
                   (OLTP)      (cache/   (objects: │ (analytics │ (experiment
                   18 tables    broker)   images,   │  star      │  tracking)
                   UUIDv7       Celery)    weights)  │  schema)   │
                                                     │
                         ┌───────────────────────────┴──────────────────┐
                         │              Celery workers                   │
                         │  worker-inference: detect → classify          │
                         │  worker-cpu:       DWH dual-write, experiments │
                         └───────────────────────────────────────────────┘
```

Five enforced architectural pillars (from the backend revamp):

1. **Async end-to-end** — FastAPI + async SQLAlchemy + async clients; nothing
   blocks the event loop.
2. **Layered** — `routers → services → repositories → ORM`. Routers are thin;
   business logic is in services; all DB access goes through repositories.
3. **Pydantic at the boundaries** — every request/response is a validated
   schema; the ORM never leaks past the service layer.
4. **Central `Settings`** — all configuration comes from one `Settings` object
   (env / file secrets); code never reads `os.environ` directly.
5. **Model traceability** — `seed_detection → inference → model_artifact` is a
   hard foreign-key chain.

---

## 3. Repository layout

```
seed-bank/
├── src/seedbank/            # Backend (FastAPI, clean architecture)
│   ├── main.py              # App factory: middleware, routers, health, lifespan
│   ├── api/                 # HTTP layer
│   │   ├── v1/              # Versioned routers (auth, analyze, batches, …)
│   │   ├── errors.py        # RFC 9457 problem-details handlers
│   │   ├── middleware.py    # RequestId + Prometheus middleware
│   │   └── rate_limit.py    # slowapi limiter wiring
│   ├── services/            # Business logic (one service per domain)
│   ├── infrastructure/      # Adapters: db, cache, storage, ml, analytics, mlflow, oauth
│   ├── schemas/             # Pydantic request/response models
│   ├── domain/              # Domain entities (e.g. user roles)
│   ├── core/                # config, logging, metrics, tracing, sentry
│   ├── workers/             # Celery app + tasks (analyze, experiment, dwh)
│   └── bootstrap/           # One-shot startup helpers (e.g. seed reference data)
├── frontend/                # Web app (React 18 + Vite + Tailwind + TanStack Query)
├── mobile/                  # Mobile app (Expo SDK 52 / React Native, realtime camera)
├── alembic/                 # Postgres migrations
├── ops/                     # Prometheus/Grafana/observability config
├── scripts/                 # register_model.py, seed_dev.py, smoke.sh, …
├── secrets/                 # File-based prod secrets (gitignored contents)
├── models/                  # Local .pth weights (NOT in git; MinIO is source of truth)
├── docs/                    # This file + diagrams/, adr/, operations.md, revamp-status.md
├── compose.yaml             # Dev stack (all services)
├── compose.prod.yaml        # Production overlay (file secrets, hardening)
├── Dockerfile               # Multi-stage (9 stages: 4 builders + 5 runtimes — see §7.4)
├── Makefile                 # Developer workflow entrypoints
└── pyproject.toml / uv.lock # Python deps (managed with uv)
```

---

## 4. Backend (FastAPI)

### 4.1 Tech stack

Python 3.12 · FastAPI · async SQLAlchemy 2 + asyncpg · Pydantic v2 +
pydantic-settings · Alembic · Celery (Redis broker) · miniopy-async (S3/MinIO) ·
clickhouse-connect · MLflow · authlib (OAuth) · slowapi (rate limiting) ·
structlog · OpenTelemetry · Sentry · Prometheus.

### 4.2 Application factory & request lifecycle

[`src/seedbank/main.py`](../src/seedbank/main.py) `create_app()` wires, in order:

- **Middleware** (registered LIFO; outermost listed first): `RequestIdMiddleware`
  (assigns/propagates a `request_id` onto every log line), `PrometheusMiddleware`
  (handler-only latency/metrics), `CORSMiddleware` (origins from
  `cors_allow_origins`), `SessionMiddleware` (needed by the OAuth `state`
  round-trip).
- **Error handlers** — `install_error_handlers` renders every error as an
  **RFC 9457 problem-details** JSON body (`type`, `title`, `status`, `detail`,
  plus a correlating `request_id`).
- **Rate limiter** — `install_rate_limiter` (slowapi, Redis-backed).
- **Routers** — the aggregated v1 router (see §4.4).
- **Tracing** — OTel instruments FastAPI *after* routers are mounted (no-op
  unless `OTEL_EXPORTER_OTLP_ENDPOINT` is set).
- **Health/metrics endpoints** — `/healthz` (liveness), `/readyz` (probes
  Postgres, Redis, MinIO, ClickHouse and returns per-component status; ClickHouse
  is allowed to degrade without failing readiness), `/metrics` (Prometheus).

`lifespan` eagerly constructs the DB sessionmaker, Redis, and storage singletons
at startup (so cold-start cost is outside the request path), bootstraps MinIO
buckets, and disposes everything on shutdown.

### 4.3 Configuration ([`core/config.py`](../src/seedbank/core/config.py))

A single `Settings` (pydantic-settings) object is the **only** source of config.
Values come from environment variables, an `.env` file (dev), or **file secrets**
under `/run/secrets` (prod — pydantic reads each file named after a field). Key
groups:

- **Service identity**: `env` (dev/test/staging/prod), `service_name`, `log_level`.
- **HTTP**: `api_v1_prefix` (`/api/v1`), `cors_allow_origins` (comma-separated or
  JSON array), `trusted_hosts`.
- **Auth**: `jwt_secret`, `jwt_algorithm` (HS256), `jwt_access_ttl_seconds`
  (15 min), `jwt_refresh_ttl_seconds` (7 days), `bcrypt_rounds`,
  `api_key_prefix` (`seedbank_`), Google/GitHub OAuth client id/secret,
  `bootstrap_token` (first-admin tripwire).
- **Datastores**: `postgres_dsn` (+ pool tuning), `redis_dsn`, Celery broker/result
  URLs, MinIO endpoint/keys/buckets (+ a separate `minio_public_endpoint` used
  **only** to sign browser-facing presigned GET URLs), ClickHouse host/creds,
  MLflow tracking URI.
- **Inference / analyze**: `inference_default_backend`
  (`torch_local`/`roboflow`/`ultralytics_yolo`), image size/pixel caps,
  `analyze_max_files_per_request` (16), allowed MIME types, per-minute rate caps.
- **Toggles**: `dwh_enabled` (OLTP→ClickHouse dual-write), `enable_metrics`,
  `otel_exporter_otlp_endpoint`, `sentry_dsn`, `celery_task_always_eager`
  (tests run tasks inline).

### 4.4 API surface

All routers are mounted under `/api/v1`
([`api/v1/__init__.py`](../src/seedbank/api/v1/__init__.py)). Interactive docs at
`/api/v1/docs`; OpenAPI schema at `/api/v1/openapi.json` (the web app's typed
client is generated from this — see §5.3).

| Router | Responsibility (representative endpoints) |
|---|---|
| `auth` | `register`, `verify-email`, `login`, `refresh`, `logout`, OAuth start/callback (Google/GitHub), one-shot `bootstrap-admin`. |
| `users` | `GET /users/me`, admin user list & role management. |
| `api_keys` | Create/list/revoke personal API keys (hashed at rest, scopes, expiry). |
| `models` | Register model artifacts, list/get, promote lifecycle, `GET /models/{id}/performance`. |
| `traffic` | Manage weighted A/B `traffic_splits` (admin). |
| `analyze` | `POST /analyze` — multipart image upload that starts a batch. |
| `batches` | List/get batches, `GET /batches/{id}` (poll for results), delete, bulk-delete, CSV/JSON export, annotated PNG, **share-link** create/revoke. |
| `analytics` | Aggregated detection/quality metrics over a time window. |
| `shared` | `GET /shared/{token}` — public, unauthenticated read-only batch report. |
| `catalog` | Reference data: seed types, suppliers. |
| `datasets` | Labelled datasets + items for offline evaluation. |
| `experiments` | Create/list/get experiments; offline-eval runs. |

**Conventions used everywhere:**

- **Envelopes** — successful single responses are `{ "data": <object> }`;
  list responses are `{ "data": [...], "meta": { page, page_size, total,
  has_more } }`.
- **Errors** — RFC 9457 problem details with a `request_id`.
- **Numeric precision** — `confidence` and bounding-box coordinates are emitted
  as decimal **strings** (NUMERIC columns) to avoid float drift; clients parse
  to numbers only at render time.

### 4.5 Authentication, authorization & security

- **Local auth** — email/password (bcrypt). Registration sends a verification
  email; `verify-email` confirms a token.
- **Tokens** — short-lived JWT **access** token + long-lived **refresh** token.
  Refresh tokens **rotate** on use with **replay detection** (a reused old token
  invalidates the chain). Clients store tokens and transparently refresh once on
  a `401`, then retry the original request.
- **OAuth** — Google and GitHub social login (authlib; `SessionMiddleware`
  carries the `state` across the redirect).
- **API keys** — personal programmatic tokens, **hashed at rest**, prefixed
  (`seedbank_`), with optional scopes and expiry; shown in plaintext exactly once
  at creation.
- **RBAC** — three roles: **`end_user`** (farmer; analyze + own history),
  **`ai_developer`** (+ models/datasets/experiments, model override at analyze
  time), **`admin`** (+ traffic splits, user management). Role gates exist on
  both the API and the clients' routing.
- **Rate limiting** — per-route caps (login/register/refresh/analyze and a
  global default), Redis-backed via slowapi.
- **Audit log** — append-only record of sensitive actions.
- **First-admin bootstrap** — `POST /auth/bootstrap-admin` guarded by a shared
  `bootstrap_token`; idempotent (409 if an admin exists), disabled (503) when the
  token is unset.

### 4.6 Data model (Postgres OLTP)

Async SQLAlchemy over Postgres, **all 18 tables**, **UUIDv7 primary keys** (time-
ordered, index-friendly), Alembic-managed. Repositories
([`infrastructure/db/repositories/`](../src/seedbank/infrastructure/db/repositories/))
are the only code that touches the ORM. The complete set (grouped):

- **Identity & auth** (5): `users`, `refresh_tokens`, `oauth_accounts`,
  `api_keys`, `audit_log`.
- **Reference / catalog** (2): `seed_types`, `suppliers`.
- **Inference graph** (4 — the traceability chain):
  - `scan_batches` — one per `POST /analyze`; carries the **state machine**
    (`pending → running → succeeded / partial / failed`), image count, duration,
    optional geo metadata.
  - `scan_images` — the uploaded images of a batch (stored in MinIO).
  - `inferences` — one model run over an image: `backend`, `model_id`,
    `latency_ms`, optional `error`.
  - `seed_detections` — one per detected seed: normalized bbox
    (`box_x_norm/y_norm/w_norm/h_norm`), `confidence`, `quality`
    (`good`/`bad`/null), `seed_type_id`, linked to its `inference`.
- **ML platform** (7): `model_artifacts` (registered weights + metadata +
  lifecycle status), `model_metrics` (per-model performance records behind
  `GET /models/{id}/performance`), `traffic_splits` (weighted A/B routing),
  `datasets` + `dataset_items` (offline-eval ground truth), `experiments` +
  `experiment_results` (offline-eval runs and their computed metrics).

### 4.7 The AI / ML platform (deep dive)

This is the heart of the product. It is worth understanding in full.

#### 4.7.1 What the AI actually does — a two-stage pipeline

Quality-checking a photo of seeds is **two distinct ML problems**, solved by two
different models in sequence:

1. **Detection ("where are the seeds?")** — an **object-detection** model scans
   the whole image and returns a **bounding box + confidence + class** for every
   individual seed it finds. One photo → N located seeds. The class identifies
   the *crop* (e.g. `coffee` or `maize`).
2. **Classification ("is this seed good or bad?")** — for **each** detected seed,
   the system **crops** that bounding box out of the original image and feeds the
   crop to a **binary image classifier** that returns `good` / `bad` + a
   confidence. The crop is routed to the classifier trained for that seed type
   (coffee crops → the coffee classifier, maize → the maize classifier).

So the data fans out: `1 image → N detections → N quality labels`. Aggregate
metrics (seed count, good-rate, confidence distribution, per-type breakdown) are
computed from that detection graph. **Detection and classification are recorded
as separate `inferences` rows** over the same image, so a detector and a
classifier can be versioned, swapped, and A/B-tested completely independently.

```
        ┌──────────────────────── one uploaded image ───────────────────────┐
        │                                                                    │
        ▼                                                                    │
  ┌───────────────┐   boxes[]              ┌──────────────────────────────┐  │
  │  DETECTION    │ ────────────► for each │  crop bbox from source image │  │
  │  model        │  (x,y,w,h,              │  → CLASSIFICATION model       │  │
  │  (Faster R-CNN│   conf, class)          │     (ResNet18+CBAM) → good/bad│  │
  │   or YOLO …)  │                         │     + confidence              │  │
  └───────────────┘                         └──────────────────────────────┘  │
        │  persist 1 inference                     │  persist 1 inference      │
        │  + N seed_detections (normalized bbox)    │  update each detection's  │
        ▼                                           ▼  quality column           │
   seed_detection ──FK──► inference ──FK──► model_artifact   (full traceability)│
        └────────────────────────────────────────────────────────────────────┘
```

#### 4.7.2 Model architectures (what's actually inside)

Architectures are **builder functions** registered under a `builder_key`
([`infrastructure/ml/builders/`](../src/seedbank/infrastructure/ml/builders/)).
A builder constructs the bare `nn.Module`; weights are then loaded into it from
MinIO. The currently wired architectures:

- **Detection — Faster R-CNN (`faster-rcnn-combined-v1`)**
  ([`faster_rcnn_combined_v1.py`](../src/seedbank/infrastructure/ml/builders/faster_rcnn_combined_v1.py)):
  torchvision `fasterrcnn_resnet50_fpn` (ResNet-50 backbone + Feature Pyramid
  Network) with a **3-class head** `[background, coffee, maize]`. The model
  returns `boxes`/`scores`/`labels`; the backend filters by
  `confidence_threshold`, normalizes pixel boxes to `[0,1]`, and caps at
  `max_detections`. Class id → name via `{0: background, 1: coffee, 2: maize}`.

- **Classification — ResNet18 + CBAM (`resnet18-cbam-coffee-v3`,
  `resnet18-cbam-maize-v4`)**
  ([`resnet18_cbam_coffee_v3.py`](../src/seedbank/infrastructure/ml/builders/resnet18_cbam_coffee_v3.py)):
  an ImageNet-pretrained **ResNet-18** backbone with a **CBAM** (Convolutional
  Block Attention Module — channel + spatial attention, see
  [`_cbam.py`](../src/seedbank/infrastructure/ml/builders/_cbam.py)) inserted
  after `layer4`, then **hybrid pooling** that concatenates global-average and
  global-max pools (512 + 512 → **1024 features**) into a single-logit `fc` head.
  Inference: resize to **224×224**, ImageNet normalization, forward → **sigmoid**
  → score; `label = "good" if score ≥ threshold else "bad"`, with
  `confidence = score` (good) or `1 − score` (bad). Trained with
  `BCEWithLogitsLoss`. There is one classifier **per crop type** (coffee, maize),
  which is why detections are grouped by seed type before classify.

> **Builders are append-only by convention.** If the math changes, copy to a new
> `-vN` file + key — never mutate a builder a `production` model references, or
> you silently change what a deployed model computes.

#### 4.7.3 Inference backends (pluggable engines)

A **backend** is the engine that *runs* a model. Every backend satisfies one
duck-typed `Protocol`
([`backends/base.py`](../src/seedbank/infrastructure/ml/backends/base.py)):
`detect(image, DetectionConfig) -> list[Detection]` and
`classify(crop, ClassificationConfig) -> Classification`, returning
**framework-free DTOs** (`BoundingBox`, `Detection`, `Classification`) so torch
never leaks up the layers. Three backends are registered
([`backends/`](../src/seedbank/infrastructure/ml/backends/)):

| Backend (`model_backend`) | Engine | Notes |
|---|---|---|
| `torch_local` | Local PyTorch from MinIO weights | **Default.** Builds the module via the registry, loads the state dict (`weights_only=True`, `strict=False`), runs the forward pass in a worker thread (`asyncio.to_thread`) so the event loop stays responsive. CUDA used when available. |
| `yolo` (`ultralytics_yolo`) | Ultralytics YOLO | Loads `.pt` weights into an `ultralytics.YOLO` (needs a filesystem path; the manager spools the bytes to a temp file). |
| `roboflow` | Hosted Roboflow inference | Network-bound; no local weights. |

Adding a backend = write a class matching the protocol and register it in the
factory ([`pipeline/factory.py`](../src/seedbank/infrastructure/ml/pipeline/factory.py)).
Heavy imports (torch, ultralytics) live **inside method bodies**, so the API
process never imports torch — only the inference worker does (this is why the API
container is small).

#### 4.7.4 Model registry & lifecycle

Weights are uploaded to MinIO and recorded in the **`model_artifacts`** table
(via `scripts/register_model.py` or `POST /models`). Each row carries: `kind`
(`detection`/`classification`), `backend`, `artifact_uri` (MinIO key), a
`builder_key`, a free-form **`config`** JSON (per-model knobs:
`confidence_threshold`, `iou_threshold`, `max_detections`, `image_size`,
`threshold`), an optional `seed_type_id`, and a **lifecycle status**:
`registered → staging → production → archived` (promotion is an API action).
Only `staging`/`production` models are eligible to serve requests (a
`registered`/`archived` model can't be used as an override).

#### 4.7.5 Model manager — loading & caching
([`infrastructure/ml/manager.py`](../src/seedbank/infrastructure/ml/manager.py))

One `ModelManager` per worker process holds a **process-wide LRU cache** of
loaded modules (default `max_models=4`, separate caches for torch and YOLO).
Loading: build module via registry → fetch weights from MinIO → load state dict →
move to CUDA/CPU → `eval()`. It serializes concurrent loads of the **same**
`model_id` through a per-id `asyncio.Lock` (so two tasks never duplicate a GPU
load), LRU-evicts to bound GPU memory, and **hot-reloads** a model when its
`model_artifacts.updated_at` advances. Pipelines are cheap, created per request;
the expensive weights live here.

#### 4.7.6 Traffic router — model selection & A/B testing
([`services/traffic_router.py`](../src/seedbank/services/traffic_router.py))

Given a **segment** `(kind, seed_type_id)`, the router decides *which* model runs:

1. Read active rows from **`traffic_splits`** for the segment (60 s Redis cache).
2. If splits exist, route by a **sticky bucket** = `hash(user_id) % 100` against
   the cumulative weights — the **same user always lands on the same model**
   (stable A/B), and traffic is uniform across the user base.
3. If no splits, fall back to the **`production`** model for that seed type, then
   to the **global** (seed-type-agnostic) production model. This makes per-type
   promotion *optional* — a deployment can promote one global model and every
   scan (including the mobile point-and-shoot flow, which sends **no** seed type)
   routes to it.
4. If still nothing, raise `ModelNotReadyError` → the user gets a clear "no model
   is available" failure (not a blank error).

`ai_developer`/`admin` can **override** the model with an explicit `model_id` at
analyze time (must be `staging`/`production`, must match the requested `kind`).

### 4.8 The end-to-end inference flow (orchestration)

```
POST /api/v1/analyze  (multipart: files[] + optional seed_type_id/supplier_id/
                       model_id/country_code/gps)
   AnalysisService (services/analysis_service.py) — load-bearing ordering:
        │  1. validate EVERY file first (count ≤16, size, MIME, real image via PIL)
        │  2. write images → MinIO  (BEFORE the DB commit, so committed rows
        │       always reference reachable objects)
        │  3. create scan_batch (pending) + scan_images, write audit log, COMMIT
        │  4. dispatch one Celery task per image (queue=inference) AFTER commit
        ▼
Celery  worker-inference   task: seedbank.analyze_image   (workers/tasks/analyze.py)
        │  fresh AsyncSession (workers never share the API engine)
        │  CAS  pending → running   (only the first task to arrive wins; sets started_at)
        │  fetch image bytes ← MinIO
        │  ── DETECT ───────────────────────────────────────────────────────────
        │     resolve detection model (override OR traffic router)
        │     run detect (torch forward in a thread) → boxes/scores/labels
        │     persist 1 inference row + N seed_detections rows
        │        (normalized bbox NUMERIC, confidence, px dims, aspect ratio;
        │         each detection's seed_type = request override, else mapped from
        │         the detector's class name coffee/maize → catalog id)
        │  ── CLASSIFY ─────────────────────────────────────────────────────────
        │     GROUP detections by seed_type
        │     for each group: resolve its classifier (router) → crop each seed
        │        from the source image (JPEG) → classify → good/bad + confidence
        │     bulk-update each detection's `quality`; add 1 classify inference row
        │  ── FINALISE ─────────────────────────────────────────────────────────
        │     when every image in the batch has a detect inference:
        │       CAS running → succeeded | partial | failed   (+ finished_at, duration)
        ▼
        (each persisted batch / inference / detection dual-writes to ClickHouse)
        ▼
GET /api/v1/batches/{id}   ← web & mobile poll every ~2s until a terminal status
```

Key properties:

- **Concurrency-safe state machine.** Batch transitions use **compare-and-set**
  updates (`pending→running`, `running→terminal`), so multiple workers
  processing a multi-image batch can't corrupt state; exactly one task owns each
  transition.
- **Per-seed-type routing within one image.** A mixed photo (some coffee, some
  maize) is detected once, then **grouped by seed type**; each group goes to its
  own classifier. A detection whose class has **no** registered classifier is
  simply left **unclassified** (not an error).
- **Crops are derived, never stored.** Bounding boxes are the source of truth in
  normalized `[0,1]`; the worker multiplies by the source image's pixel
  dimensions to cut each crop at classify time.
- **Pixel precision.** `confidence` is `NUMERIC(5,4)`, bbox columns are
  `NUMERIC(7,6)` — the worker rounds and passes `Decimal` so SQLAlchemy never
  coerces floats into a mismatched scale.

#### 4.8.1 Error handling & terminal states

- `ExternalServiceError` (MinIO/Redis hiccup) → Celery **auto-retries** (up to 2).
- **No routable model** → batch `failed` with a human-readable `error_message`
  ("An administrator must register and promote a detection model.") surfaced to
  the clients, so the app never shows a blank failure. (The mobile flow sends no
  seed type, so it hits this first if nothing is promoted.)
- **Detect crashes** → the inference row's `error` is recorded and the batch is
  `failed`.
- **Classify crashes** (after detect already persisted) → detect data is kept and
  the batch degrades to **`partial`** (never throws away good detection results).
- A clean run with every image detected and classified → **`succeeded`**.

#### 4.8.2 What the platform supports (summary)

Multiple **crop types** (coffee, maize today; more via new builders + classifiers)
· **per-seed-type** classifiers with independent A/B · **mixed batches** ·
the **mobile point-and-shoot** flow (no seed type → global model) ·
**multiple backends** (local torch, YOLO, hosted Roboflow) · **GPU or CPU** ·
**hot model reload** without a restart · **weighted A/B traffic splits** with
sticky per-user assignment · **per-request model override** for developers ·
**offline evaluation** of any model against labelled datasets (§4.9) · and full
**traceability** from every seed label back to the exact model version that
produced it.

### 4.9 Experiments, datasets & MLflow

- **Datasets** — labelled images + items, stored in MinIO + Postgres, used as
  ground truth for offline evaluation.
- **Experiments** — `POST /experiments` runs a model over a dataset offline,
  computes classification metrics (confusion matrix, etc. — see
  [`services/eval/`](../src/seedbank/services/eval/)), logs params/metrics/
  artifacts to **MLflow**, writes a Markdown report to MinIO, and surfaces results
  via `GET /models/{id}/performance`. The runner task is
  [`workers/tasks/experiment.py`](../src/seedbank/workers/tasks/experiment.py).

### 4.10 Data warehouse (ClickHouse)

Analytics are served from a **ClickHouse star schema** populated by an
**app-level dual-write** (not CDC): when `dwh_enabled`, the API/workers dispatch a
Celery task ([`workers/tasks/dwh.py`](../src/seedbank/workers/tasks/dwh.py)) that
writes to dimension + fact tables (`ReplacingMergeTree`, partitioned by month).
This keeps heavy analytical queries off the OLTP Postgres. The `analytics` router
and the web Analytics page read from here.

### 4.11 Workers (Celery)

[`workers/celery_app.py`](../src/seedbank/workers/celery_app.py) defines the app;
Redis is the broker (DB 1) and result backend (DB 2). There are **two worker
containers**, each subscribed to a disjoint set of queues so the heavy ML
dependencies never load into the lightweight worker:

| Container | `-Q` queues it consumes | Workload | Image target | Concurrency |
|---|---|---|---|---|
| `worker-inference` | `inference`, `evaluation` | detect→classify pipeline; offline-eval model runs | `runtime-inference-cpu` (slim torch) — swappable to `…-full` (YOLO/Roboflow) or `runtime-gpu` | 2 (`WORKER_INFERENCE_CONCURRENCY`) |
| `worker-cpu` | `default`, `cdc`, `housekeeping`, `experiments`, `dwh` | DWH dual-write, experiment bookkeeping, CDC/housekeeping (declared, mostly stubs) | `runtime-cpu` (no torch) | 2 (`WORKER_CPU_CONCURRENCY`) |

Why the split: `torch`/`torchvision` live in the `[inference]` dependency extra
and are intentionally **absent** from the CPU runtime image, so a routine DWH
write never pays a ~1.6 GB torch import. Both workers cap concurrency explicitly
(`--concurrency=2`) and recycle children (`--max-tasks-per-child`) because
Celery's default (host-CPU count) would fork ~12 prefork children that each
lazily load torch + a model and OOM the memory cap. `celery_task_always_eager`
(a `Settings` toggle) makes tasks run **inline in-process** during tests, which is
also how worker-side metrics surface on the integration-test path.

### 4.12 Observability (the four signals)

Observability is a first-class concern (the backend's "Phase 9"). Four signals —
**logs, metrics, traces, errors** — plus health probes, all centralised in
[`core/`](../src/seedbank/core/) so labels/format stay consistent. The dashboards
and scrape config that consume them live in [`ops/`](../ops/) (§7.5).

#### 4.12.1 Structured logging — [`core/logging.py`](../src/seedbank/core/logging.py)
`structlog` configured once at process start. **Pretty colourised console** in
`dev`; **one-JSON-object-per-line** in every other env (machine-parseable for a
log aggregator). Every event is enriched with **context vars** bound per request —
`request_id` and `path` are bound by `RequestIdMiddleware`, so *every* log line
emitted while handling a request is automatically correlatable. Rule: always log
via `structlog.get_logger(__name__)`, never the stdlib `logging` module, or the
contextvars won't attach.

#### 4.12.2 Metrics — Prometheus ([`core/metrics.py`](../src/seedbank/core/metrics.py))
A **dedicated `CollectorRegistry`** (not the global default — avoids
"Duplicated timeseries" when test fixtures rebuild the app) owns every metric.
`PrometheusMiddleware` ([`api/middleware.py`](../src/seedbank/api/middleware.py))
records HTTP signals; services/workers increment the domain counters directly.
The full set the service emits:

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `http_requests_total` | counter | `method, path, status` | requests by route **template** + 2xx/3xx/4xx/5xx class |
| `http_request_duration_seconds` | histogram | `method, path` | latency (buckets 5 ms → 10 s) |
| `http_requests_inflight` | gauge | `method` | concurrent in-flight requests |
| `seedbank_inference_total` | counter | `kind, backend, status` | model inferences (`detection`/`classification` × backend × `ok`/`error`) |
| `seedbank_inference_duration_seconds` | histogram | `kind, backend` | per-image inference latency (50 ms → 30 s) |
| `seedbank_dwh_dispatch_total` | counter | `task, result` | OLTP→ClickHouse dispatch attempts (`ok`/`disabled`/`error`) |
| `seedbank_dwh_task_duration_seconds` | histogram | `task, result` | worker-side DWH sync time |
| `seedbank_experiment_run_total` | counter | `status` | offline-eval runs by terminal status |
| `seedbank_auth_login_total` | counter | `result` | logins (`ok`/`invalid_credentials`/`blocked`) |

**Cardinality discipline** (the reason metrics don't melt Prometheus): the `path`
label is always the **Starlette route template** (`/api/v1/batches/{id}`), never
the raw URL — resolved by re-walking the router *after* the handler runs; an
unmatched path collapses to `"_unmatched"`. Status codes are bucketed into
classes, not kept per-code. The inflight gauge is method-only (gauges retain
label sets forever). `/metrics` is excluded from its own histograms. Prometheus
adds a **second** guard: a `metric_relabel_config` drops any series whose `path`
still looks like a UUID (fail-safe if templating ever regresses). Exposed at
`GET /metrics` in Prometheus text format.

#### 4.12.3 Tracing — OpenTelemetry ([`core/tracing.py`](../src/seedbank/core/tracing.py))
A single `TracerProvider` with an **OTLP** span exporter and auto-instrumentation
across every IO boundary the service crosses: **FastAPI** requests, **SQLAlchemy +
asyncpg**, **Redis**, outbound **httpx**, and **Celery** tasks — so a trace can
follow a request from the API through the queue into a worker's DB calls.
**Opt-in and idempotent**: a complete no-op unless `OTEL_EXPORTER_OTLP_ENDPOINT`
is set (the dev stack stays free of exporters dialing a dead collector). The API
initialises it in the FastAPI lifespan; Celery re-initialises **per forked
worker** (via `worker_process_init`, because forking after init breaks the OTLP
gRPC channel). Each instrumentor is wrapped in try/except — tracing is best-effort
and never crashes a request.

#### 4.12.4 Error & performance monitoring — Sentry ([`core/sentry.py`](../src/seedbank/core/sentry.py))
Initialised once per process; **no-op unless `SENTRY_DSN` is set**. Uses Sentry's
FastAPI + Celery integrations (request context, user, unhandled exceptions
captured automatically). **`send_default_pii=False`** — we never ship PII;
`request_id` already flows through structlog for cross-system correlation. Sample
rates default conservatively and are env-tunable in production.

#### 4.12.5 Health & readiness probes ([`main.py`](../src/seedbank/main.py))
- **`GET /healthz`** — liveness; cheap, no dependencies (is the process up?).
- **`GET /readyz`** — readiness; actively probes **Postgres, Redis, MinIO,
  ClickHouse** and returns each component's status. ClickHouse is allowed to
  **degrade without failing** readiness (analytics is non-critical to serving).
  This is the endpoint Docker healthchecks and an orchestrator's readiness gate
  hit.
- **`GET /metrics`** — the Prometheus scrape target (§4.12.2).

---

## 5. Web frontend (`frontend/`)

### 5.1 Tech stack

React 18 · TypeScript · Vite · Tailwind CSS (CSS-variable theme tokens) · shadcn/
radix UI primitives · TanStack Query (server state) · React Router v6 · React
Hook Form + Zod · openapi-fetch + openapi-typescript (typed client generated from
the backend's OpenAPI) · sonner (toasts) · Vitest + Testing Library.

### 5.2 Architecture

Feature-sliced under `frontend/src/`:

```
src/
├── main.tsx            # Providers: I18n → Theme → QueryClient → Auth → Router
├── router.tsx          # Route table; lazy-loaded feature pages; role guards
├── components/
│   ├── layout/         # AppShell (sidebar + topbar), nav config
│   ├── ui/             # shadcn primitives (button, dialog, select, table, …)
│   ├── shared/         # cross-feature widgets (states, pagination, dropzone,
│   │                   #   bbox-overlay, status-badge, page-header, …)
│   ├── theme/          # light/dark theme provider + toggle
│   └── guards/         # ProtectedRoute, RoleRoute
├── features/<name>/    # api.ts + pages/ + components/ per feature
│   (auth, dashboard, analyze, batches, analytics, compare, profile,
│    api-keys, models, datasets, experiments, traffic, users, catalog)
├── i18n/               # localization system (see §5.4) — NEW
└── lib/                # api client, env, format, query-client, auth/token-store
```

### 5.3 API client & data flow

[`lib/api/client.ts`](../frontend/src/lib/api/client.ts) is one typed
`openapi-fetch` client built from the generated `schema.d.ts` (run `npm run
gen:api` to regenerate from `openapi.json`). A middleware injects the bearer
token and **transparently refreshes once on a 401** (deduplicating concurrent
refreshes), then retries. `unwrap()` turns an openapi-fetch result into resolved
`data` or a typed `ApiError` throw, so components only ever see data or a typed
error. All server state flows through **TanStack Query** hooks defined in each
feature's `api.ts`.

### 5.4 Localization (EN / AR with full RTL) — recent work

A **dependency-free, fully-typed** i18n system under `frontend/src/i18n/`:

- **Source of truth** — `dictionaries/en.ts` is a flat dictionary; `keyof typeof
  en` becomes `TranslationKey`. `dictionaries/ar.ts` is typed `Record<
  TranslationKey, string>`, so a **missing or extra Arabic key is a compile
  error** — the UI can never half-fall-back to English.
- **Hook** — `useI18n()` returns `{ t, tn, locale, setLocale, dir }`. `t(key,
  params)` interpolates `{name}` tokens; `tn(key, count)` selects the correct
  **plural** form (English one/other; Arabic uses the full CLDR set zero/one/two/
  few/many/other).
- **Provider** — sets `<html lang dir>`, persists choice to `localStorage`,
  detects the initial locale from storage → browser → default.
- **RTL** — Arabic flips the entire layout. Achieved by converting directional
  Tailwind utilities to **logical properties** (`ms-`/`me-`/`ps-`/`pe-`/`start-`/
  `end-`/`text-start`) in the shared UI primitives (dialog, dropdown, select,
  table) and pages, plus direction-aware chevrons and a drawer that opens from
  the correct edge. Numbers stay Latin digits in Arabic for cross-script
  consistency; dates are formatted with the active locale.
- **Switcher** — a language picker in the topbar and on the auth/share pages.
- **Coverage** — the **entire end-user surface** is translated (auth, dashboard,
  analyze, batches, batch detail, analytics, compare, profile, api-keys, the
  public shared report, the shell, and all shared components). The admin/ML
  pages (models, datasets, experiments, traffic, users) are intentionally
  English — they are role-gated to developers/admins and never reached by
  farmers.
- **Tests** — `i18n/translate.test.ts` (interpolation, plural rules, dictionary
  parity) and `i18n/i18n-provider.test.tsx` (switching to Arabic flips `dir` to
  RTL, changes rendered text, and persists).

### 5.5 Pages & features (end-user journey)

- **Auth** — login, register (with email verification flow), verify-email; a
  field-pattern backdrop, theme + language toggles before sign-in.
- **Dashboard** — welcome, KPI strip (scans, images, success rate, 14-day
  sparkline), quick actions, recent scans.
- **Analyze ("Check seeds")** — drag/drop or pick photos, optional metadata
  (seed type, supplier, country, GPS, dev-only model override), submit → starts a
  batch and navigates to its detail.
- **Batches / Scan history** — paginated table, multi-select bulk delete.
- **Batch detail** — polls until terminal; shows an **AI insights** panel
  (quality donut + confidence histogram + headline stats), a per-seed-type
  breakdown, and per-image cards with an **interactive bounding-box overlay**
  (filter by quality, confidence threshold, toggle labels). Actions: export
  (CSV/JSON), **share** (create a public read-only link), delete.
- **Analytics** — windowed (7/30/90d) trends, confidence distribution, quality
  by seed type, from the ClickHouse warehouse.
- **Compare** — pick 2–10 scans, see metrics side-by-side with the best column
  highlighted.
- **Profile / API keys** — account details; create/reveal-once/revoke API keys.
- **Public shared report** (`/shared/:token`) — unauthenticated, read-only batch
  summary, also localized with its own language/theme toggles.
- **ML-platform pages** (role-gated) — models, datasets, experiments, traffic
  splits, users.

### 5.6 Design system

An "agricultural green" theme: a deep leaf-green primary, warm amber accents,
a warm off-white field in light mode and a soil-night palette in dark mode, all
as HSL CSS variables so light/dark swap without a rebuild. Calm motion: gentle
page fade/rise transitions, animated count-ups, a two-stage "analyzing" shimmer
that mirrors the real detect→classify pipeline.

---

## 6. Mobile app (`mobile/`)

A new **Expo SDK 52 / React Native** app focused on farmers in the field —
realtime camera capture with the same bilingual EN/AR + RTL experience.

### 6.1 Tech stack

Expo SDK 52 · React Native 0.76 · TypeScript · `expo-camera` (realtime) ·
React Navigation v7 (bottom tabs + native stack) · TanStack Query ·
`expo-secure-store` (token keystore) · `@react-native-async-storage/async-storage`
(prefs) · `expo-updates` (RTL reload) · Ionicons.

### 6.2 Architecture

```
mobile/src/
├── api/           # fetch client (auth + 401-refresh), auth, batches/analyze,
│                  #   tokens (secure-store), config (runtime-overridable base URL)
├── auth/          # session context: loading → authenticated → unauthenticated
├── components/    # themed UI primitives (Button, Card, TextField, StatusPill…)
├── i18n/          # en/ar dictionaries, hand-rolled CLDR plurals, RTL provider
├── navigation/    # bottom tabs (Capture/History/Settings) + root stack (Result)
├── screens/       # login, camera, result, history, settings
└── theme/         # agricultural-green palette (light/dark) + theme context
App.tsx            # Providers: SafeArea → Theme → I18n → Query → Auth → Navigation
```

The API layer deliberately **mirrors the web client's contract**: `{data}`
envelopes, the same `/api/v1/...` paths, bearer auth with single refresh-on-401,
and multipart upload to `POST /api/v1/analyze`.

### 6.3 Realtime camera flow (the headline feature)

[`screens/camera-screen.tsx`](../mobile/src/screens/camera-screen.tsx):
live `CameraView` preview with a center framing guide → tap the shutter to
capture (multi-shot; thumbnails strip; remove any) → "Check seeds (N)" uploads
all photos as multipart to `/analyze` → navigates to the **Result** screen, which
**polls** the batch via TanStack Query until terminal and shows the good-rate,
seed counts, and confidence. Camera permission is requested with a friendly
gate; the camera can flip front/back.

### 6.4 Localization & RTL on native

Same EN/AR model as web, but RN-specific: plural categories are computed by hand
(Hermes ships only a partial `Intl`), the locale persists to AsyncStorage, and
**RTL** is applied via `I18nManager.forceRTL` — which React Native only mirrors
on the **next launch**, so switching to/from Arabic triggers an `expo-updates`
reload in production builds. Dates use a Hermes-safe `DD/MM/YYYY HH:mm` formatter
with Latin digits.

### 6.5 Auth & configurable server

Tokens live in the OS keystore (`expo-secure-store`), mirrored in memory for
synchronous read by the request middleware. The API base URL defaults to
`app.json → extra.apiBaseUrl` but is **overridable from Settings** (on a physical
phone `localhost` is the phone itself, so testers point it at the dev machine's
LAN IP).

### 6.6 Running the mobile app

```bash
cd mobile && npm install && npm start   # press a (Android) / i (iOS), or scan
                                        # the QR with Expo Go (same Wi-Fi)
```
Camera needs a real device or an emulator with a virtual camera. See
[`mobile/README.md`](../mobile/README.md).

---

## 7. Infrastructure & operations

The entire system — application **and** every backing service, admin UI, and the
observability stack — runs from a single [`compose.yaml`](../compose.yaml) on a
laptop. This section documents every container, how to reach it, the build
images behind them, and the operational tooling.

### 7.1 Docker Compose services (dev: `compose.yaml`)

Services are grouped by **compose profiles** so `make up` stays lean and you opt
into the heavier extras. All host ports are bound to **`127.0.0.1`** (never
exposed to the LAN by default). The shared `x-app-env` anchor feeds the same
datastore DSNs/credentials to the API and both workers.

| Service (`container_name`) | Profile | Purpose | Browser/host URL |
|---|---|---|---|
| `api` (`seedbank-api`) | *(default)* | FastAPI app (routers→services→repos) | http://localhost:8000 · docs `/api/v1/docs` |
| `worker-inference` (`seedbank-worker-inference`) | *(default)* | Celery `inference,evaluation` — detect→classify, offline-eval | *(no port)* |
| `worker-cpu` (`seedbank-worker-cpu`) | *(default)* | Celery `default,cdc,housekeeping,experiments,dwh` — DWH + experiments | *(no port)* |
| `postgres` (`seedbank-postgres`) | *(default)* | OLTP database (Postgres 16, `wal_level=logical`) | `localhost:5432` |
| `redis` (`seedbank-redis`) | *(default)* | Cache, Celery broker (DB 1) + result (DB 2), rate-limit store; `allkeys-lru`, 256 MB | `localhost:6379` |
| `minio` (`seedbank-minio`) | *(default)* | Object store: images, weights, datasets, experiment artifacts | API `localhost:9000` · **console** http://localhost:9001 |
| `clickhouse` (`seedbank-clickhouse`) | *(default)* | Analytics warehouse (star schema) | `localhost:8123` |
| `mlflow` (`seedbank-mlflow`) | *(default)* | Experiment tracking server + UI (Postgres backend store, MinIO artifacts) | http://localhost:5000 |
| `adminer` (`seedbank-adminer`) | `dev` | Postgres web admin UI | http://localhost:8080 |
| `ch-ui` (`seedbank-ch-ui`) | `dev` | ClickHouse web admin UI (proxies CH over the compose net) | http://localhost:3488 |
| `prometheus` (`seedbank-prometheus`) | `obs` | Metrics scraper + TSDB (7-day retention) | http://localhost:9090 |
| `grafana` (`seedbank-grafana`) | `obs` | Dashboards (auto-provisioned datasource + dashboard) | http://localhost:3000 |
| `frontend` (`seedbank-frontend`) | `frontend` | **Built** web app served by nginx | http://localhost:5173 |

**Production hardening** ([`compose.prod.yaml`](../compose.prod.yaml) overlay):
swaps the inference worker to the **`runtime-gpu`** image with a GPU device
reservation, reads **file secrets** instead of env, and locks down ports.

Every service declares a **healthcheck** and tight CPU/memory `deploy.limits`
(e.g. the inference worker is capped at 2 CPU / 4 GB because CPU torch can spike
to ~2 GB on first inference; Grafana **fails closed** — it refuses to start
unless `GRAFANA_PASSWORD` is set). `depends_on … condition: service_healthy`
gives a correct boot order (API waits for Postgres/Redis/MinIO/ClickHouse to be
healthy).

> **Note on CORS for local dev:** the API only allows the origins in
> `CORS_ALLOW_ORIGINS` (compose default `http://localhost:5173,http://127.0.0.1:5173`).
> The dockerized `frontend` serves the **built** app on `5173` and works out of
> the box. To run the **Vite dev server** (hot reload) against the live API,
> either serve it on `5173` (don't run the `frontend` profile) or add your dev
> origin to `CORS_ALLOW_ORIGINS` and restart the `api` service.

### 7.2 Admin & operator UIs (how to actually look inside the system)

Everything has a window you can open in a browser — no `psql`/`redis-cli`
required:

| Tool | URL | What you do there | Brought up by |
|---|---|---|---|
| **API Swagger / OpenAPI** | http://localhost:8000/api/v1/docs | Explore & call every endpoint; the web client's types are generated from `/api/v1/openapi.json` | default |
| **MinIO console** | http://localhost:9001 | Browse buckets (uploaded images, model weights, datasets, experiment reports) | default |
| **MLflow UI** | http://localhost:5000 | Compare experiment runs, params, metrics, artifacts | default |
| **Adminer** | http://localhost:8080 | Query/inspect the Postgres OLTP tables | `make up-dev` |
| **ch-ui** | http://localhost:3488 | Query/inspect the ClickHouse warehouse | `make up-dev` |
| **Prometheus** | http://localhost:9090 | Raw metric queries, target health (`/targets`) | `make up-obs` |
| **Grafana** | http://localhost:3000 | The **Seed-Bank Overview** dashboard (§7.5) | `make up-obs` |

### 7.3 Compose profiles & `make` recipes that combine them

| Command | Profiles | Brings up |
|---|---|---|
| `make up` | *(none)* | Lean stack: api + both workers + Postgres/Redis/MinIO/ClickHouse/MLflow |
| `make up-infra` | *(none)* | **Only** the datastores (fast smoke / running the app locally) |
| `make up-no-inference` | *(none)* | api + worker-cpu + infra (skip the heavy torch worker) |
| `make up-dev` | `dev` | Lean stack **+ Adminer + ch-ui** |
| `make up-obs` | `obs` | Lean stack **+ Prometheus + Grafana** |
| `make up-front` | `frontend` | Lean stack **+ the built React app (nginx :5173)** |
| `make front` | — | Run the **Vite dev server** locally on :5173 (needs `make up` for the API) |

### 7.4 Container images (multi-stage `Dockerfile`)

One [`Dockerfile`](../Dockerfile) builds every first-party image via 9 stages —
**4 builder** stages (resolve deps with `uv`) feeding **5 runnable** runtimes.
Each runtime carries exactly the dependencies its job needs, which is why the API
image is small and torch only exists where inference runs:

| Runtime target | Used by | Contains |
|---|---|---|
| `runtime-cpu` | `api`, `worker-cpu` | App + web/db/storage deps. **No torch.** |
| `runtime-inference-cpu` | `worker-inference` (default) | + **slim CPU torch + torchvision + headless cv2** (~1.6 GB) for the `torch_local` backend |
| `runtime-inference-cpu-full` | `worker-inference` (opt-in) | + **ultralytics (YOLO) + inference-sdk (Roboflow)** |
| `runtime-gpu` | `worker-inference` (prod overlay) | CUDA 12.4 base + GPU torch + device reservation |
| `mlflow` | `mlflow` | Upstream MLflow image |

### 7.5 Observability stack — Prometheus + Grafana ([`ops/`](../ops/))

`make up-obs` adds the metrics pipeline (config is all in-repo under `ops/`, so
it's reproducible and version-controlled):

- **Prometheus** ([`ops/prometheus/prometheus.yml`](../ops/prometheus/prometheus.yml))
  scrapes `api:8000/metrics` every 15 s (plus itself), keeps 7 days of TSDB, and
  applies the UUID-path `metric_relabel` cardinality guard described in §4.12.2.
  Workers don't run an embedded HTTP server, so worker metrics surface through
  the API process's shared registry (or in-process during eager test runs).
- **Grafana** auto-provisions on first boot
  ([`ops/grafana/provisioning/`](../ops/grafana/provisioning/)): the **Prometheus
  datasource** (`url: http://prometheus:9090`, set default, non-editable) and a
  file-based dashboard provider that loads
  [`ops/grafana/dashboards/seedbank-overview.json`](../ops/grafana/dashboards/seedbank-overview.json)
  into a "Seed-Bank" folder. Dashboards are **edit-locked in the UI** on purpose —
  change the JSON in-repo so edits survive a container recreate.

The **Seed-Bank — Overview** dashboard ships these panels (each wired to the
metrics in §4.12.2):

| Panel | Query (PromQL) |
|---|---|
| HTTP request rate by status class | `sum by (status) (rate(http_requests_total[5m]))` |
| HTTP p50/p95 latency by route | `histogram_quantile(0.5/0.95, sum by (le,path) (rate(http_request_duration_seconds_bucket[5m])))` |
| DWH dispatch rate by result | `sum by (result) (rate(seedbank_dwh_dispatch_total[5m]))` |
| DWH worker task p95 by task | `histogram_quantile(0.95, sum by (le,task) (rate(seedbank_dwh_task_duration_seconds_bucket[5m])))` |
| Inferences per second by kind | `sum by (kind,status) (rate(seedbank_inference_total[1m]))` |
| Login attempts (5m) | `sum by (result) (increase(seedbank_auth_login_total[5m]))` |

Grafana credentials: `GRAFANA_USER`/`GRAFANA_PASSWORD` from `.env` (anonymous
access and sign-up are disabled; gravatar off; strict same-site cookies).

### 7.6 Migrations, seeding, secrets, model registration

- **Postgres schema** — Alembic under [`alembic/`](../alembic/); `make migrate`
  (roll back one with `make migrate-down`). Postgres boots with
  `wal_level=logical` + replication slots so logical-replication CDC *can* be
  added later (today the DWH path is app-level dual-write).
- **ClickHouse schema** — idempotent star-schema DDL via `make migrate-clickhouse`.
- **Seeding** — `make seed` (runs `migrate-clickhouse` first) seeds the catalog
  (seed types/suppliers), registers models, and creates demo users.
- **Secrets** — dev uses `.env` (provisioned from `*.example` by `make env`);
  **prod uses file secrets** under `/run/secrets` (one file per `Settings` field)
  via `compose.prod.yaml` + [`secrets/`](../secrets/). `make secrets-check`
  enforces the files exist and are `chmod 0400`. Pre-commit runs **gitleaks** so
  secrets never reach git; `.env` and `secrets/*` contents are gitignored.
- **Model weights** — **not in git** (history was scrubbed to purge ~165 MB of
  `.pth`). MinIO is the source of truth; register with
  [`scripts/register_model.py`](../scripts/register_model.py) or `POST /models`,
  then promote to `production`. The app cannot infer until at least one detection
  **and** one classification model are registered and promoted.

### 7.7 Operational Make targets (run / inspect / tear down)

| Target | Does |
|---|---|
| `make ps` / `make logs` | Service status / follow all logs |
| `make wait` | Block until the API healthcheck passes |
| `make down` | Stop & remove containers (**keeps** volumes/data) |
| `make down-volumes` | Stop **and wipe** all volumes — total reset |
| `make restart` | `down` then `up` |
| `make up-prod` / `down-prod` / `logs-prod` | Production overlay lifecycle (secrets-checked, GPU on) |
| `make image-sizes` / `make image-bloat` | Inspect built image sizes / largest files |
| `make clean` | Remove caches, coverage, build artifacts |

---

## 8. Local development quickstart

```bash
# 1. Backend stack (API + workers + datastores + ML)
make up                 # or: docker compose up -d
make migrate && make migrate-clickhouse
make seed               # reference data + a dev admin
# register at least one detection + one classification model (MinIO must have weights)

# 2. Web app (hot reload)
cd frontend
cp .env.example .env    # set VITE_API_BASE_URL=http://localhost:8000
npm install && npm run dev   # serve on :5173 (allowed origin) for CORS to pass

# 3. Mobile app
cd mobile && npm install && npm start
```

Backend health: `GET http://localhost:8000/healthz` and `/readyz`. API docs:
`http://localhost:8000/api/v1/docs`.

---

## 9. Testing & quality gates

- **Backend** — pytest pyramid: `make test-unit`, `make test-integration`
  (testcontainers spin up real Postgres/Redis/etc.), `make test-e2e`, all via
  `make test`. `make check` = **lint (ruff) + typecheck (mypy, strict) +
  test-unit** (the fast pre-commit gate). `make smoke` runs
  [`scripts/smoke.sh`](../scripts/smoke.sh) against a live compose stack.
  Pre-commit runs ruff/mypy/**gitleaks**. (Caveat: integration tests are **not
  fully hermetic** — some boot the app and reach for a live Redis; see
  [`docs/revamp-status.md`](./revamp-status.md).)
- **Web** — `npm run typecheck` (tsc), `npm test` (Vitest, incl. i18n + format +
  insights + token tests), `npm run lint` (ESLint), `npm run build`.
- **Mobile** — `npm run typecheck` (tsc); validated with `expo-doctor` and a full
  `expo export` Metro bundle.

---

## 10. Known limitations / unfinished tail

Tracked in detail in [`docs/revamp-status.md`](./revamp-status.md). Highlights:

- **No CI/CD** yet (`.github/workflows/` absent).
- Test suite **not hermetic** (rate limiter dials a real Redis); no full coverage
  number is trustworthy until fixed.
- Inference upload is **multipart-only** (no presigned upload, no batch cancel).
- DWH is **app-level dual-write**, not true logical-replication CDC.
- A few service/schema-backed endpoints lack routes (password change, experiment
  results, presigned upload); `housekeeping` queue has no task; `TrafficRouter`
  queries splits ad-hoc (no repository).
- OTel/Sentry are **opt-in** (no-op unless configured).

---

## 11. Glossary

- **Batch / scan** — one `POST /analyze` submission (one or more images).
- **Detection** — a single located seed (bounding box + confidence + quality).
- **Inference** — one model run over one image (produces detections).
- **Backend (ML)** — an inference engine (`torch_local`/`yolo`/`roboflow`); not to
  be confused with the FastAPI "backend".
- **Builder** — a factory that constructs a model's architecture before loading
  weights, keyed by `builder_key`.
- **Traffic split** — weighted routing of inference requests across production
  models (A/B).
- **Good-rate** — `good / (good + bad)` over classified detections.
- **Envelope** — the `{ data, [meta] }` response wrapper.
- **DWH** — the ClickHouse data warehouse / analytics store.

---

## 12. Where to look (pointers)

| You want… | Go to |
|---|---|
| App wiring, middleware, health | [`src/seedbank/main.py`](../src/seedbank/main.py) |
| Every config knob | [`src/seedbank/core/config.py`](../src/seedbank/core/config.py) |
| HTTP endpoints | [`src/seedbank/api/v1/`](../src/seedbank/api/v1/) |
| Business logic | [`src/seedbank/services/`](../src/seedbank/services/) |
| DB access / tables | [`src/seedbank/infrastructure/db/repositories/`](../src/seedbank/infrastructure/db/repositories/) |
| ML backends / pipeline | [`src/seedbank/infrastructure/ml/`](../src/seedbank/infrastructure/ml/) |
| Celery tasks | [`src/seedbank/workers/tasks/`](../src/seedbank/workers/tasks/) |
| Metrics / logging / tracing / sentry | [`src/seedbank/core/`](../src/seedbank/core/) |
| Prometheus scrape + Grafana dashboards | [`ops/`](../ops/) |
| Compose stack / images / Make targets | [`compose.yaml`](../compose.yaml) · [`Dockerfile`](../Dockerfile) · [`Makefile`](../Makefile) |
| Web app | [`frontend/src/`](../frontend/src/) · [`frontend/README.md`](../frontend/README.md) |
| Web localization | [`frontend/src/i18n/`](../frontend/src/i18n/) |
| Mobile app | [`mobile/`](../mobile/) · [`mobile/README.md`](../mobile/README.md) |
| Backend status & roadmap | [`docs/revamp-status.md`](./revamp-status.md) |
| Operations runbook | [`docs/operations.md`](./operations.md) |
| Architecture diagrams | [`docs/diagrams/`](./diagrams/) |
| Architecture decisions | [`docs/adr/`](./adr/) |

---

## 13. Complete tool & technology index

Every external tool, library, and service the project uses, grouped by area — so
nothing is a mystery when you meet it in the code or the compose file.

**Backend runtime & framework**
- **Python 3.12** · **FastAPI** (async web framework) · **Starlette** (ASGI
  primitives / middleware) · **Uvicorn** (ASGI server) · **Pydantic v2** +
  **pydantic-settings** (validation + central config).

**Data access & datastores**
- **PostgreSQL 16** (OLTP) · **SQLAlchemy 2 (async)** + **asyncpg** (driver) ·
  **Alembic** (migrations) · **Redis 7** (cache, Celery broker/result, rate-limit
  store) · **ClickHouse** (analytics warehouse) + **clickhouse-connect** ·
  **MinIO** (S3-compatible object store) + **miniopy-async** (async S3 client).

**Async jobs & ML platform**
- **Celery** (task queue, Redis broker) · **PyTorch** + **torchvision** (Faster
  R-CNN detector, ResNet18+CBAM classifiers) · **Ultralytics YOLO** (alt backend)
  · **Roboflow inference-sdk** (hosted backend) · **Pillow** + **OpenCV
  (headless)** (image decode/crop) · **MLflow** (experiment tracking + artifact
  store) · **NumPy**.

**Auth & security**
- **bcrypt/passlib** (password hashing) · **PyJWT** (access/refresh tokens) ·
  **authlib** (Google/GitHub OAuth) · **slowapi** (rate limiting) · **gitleaks**
  (secret scanning in pre-commit). Conventions: RFC 9457 problem-details,
  hashed-at-rest API keys, refresh-token rotation with replay detection.

**Observability**
- **structlog** (structured JSON/console logs) · **prometheus-client** (metrics)
  · **Prometheus** (scrape + TSDB) · **Grafana** (dashboards) ·
  **OpenTelemetry** (OTLP traces, FastAPI/SQLAlchemy/Redis/httpx/Celery
  instrumentation) · **Sentry** (error/performance monitoring).

**Web frontend**
- **React 18** · **TypeScript** · **Vite** · **Tailwind CSS** · **shadcn/ui** on
  **Radix** primitives · **TanStack Query** (server state) · **React Router v6** ·
  **React Hook Form** + **Zod** · **openapi-fetch** + **openapi-typescript**
  (typed client generated from the backend OpenAPI) · **sonner** (toasts) ·
  **Recharts** (charts) · a **dependency-free, fully-typed i18n** system (EN/AR +
  RTL) · **Vitest** + **Testing Library** · **ESLint**.

**Mobile app**
- **Expo SDK 52** · **React Native 0.76** (Hermes) · **TypeScript** ·
  **expo-camera** (realtime capture) · **React Navigation v7** (tabs + native
  stack) · **TanStack Query** · **expo-secure-store** (token keystore) ·
  **AsyncStorage** (prefs) · **expo-updates** (RTL reload) · **Ionicons** ·
  `I18nManager.forceRTL` + hand-rolled CLDR plurals.

**Infra, build & tooling**
- **Docker** + **Docker Compose** (profiles: default / `dev` / `obs` /
  `frontend`) · multi-stage **Dockerfile** (CPU / inference-CPU / inference-full /
  GPU / MLflow) · **nginx** (serves the built web app) · **uv** (Python dependency
  manager + lockfile) · **Makefile** (developer entrypoint) · **ruff** (format +
  lint) · **mypy** (strict types) · **pytest** (+ **testcontainers**) ·
  **pre-commit** · **NVIDIA CUDA 12.4** (prod GPU runtime).

**Operator UIs**
- **Swagger/OpenAPI** (`/api/v1/docs`) · **MinIO console** · **MLflow UI** ·
  **Adminer** (Postgres) · **ch-ui** (ClickHouse) · **Prometheus UI** ·
  **Grafana**. See §7.2 for URLs.
```
