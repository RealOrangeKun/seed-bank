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

Last updated: 2026-06-25.

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
├── Dockerfile               # Multi-stage, 7 targets (api, workers, frontend, …)
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

Async SQLAlchemy over Postgres, **18 tables**, **UUIDv7 primary keys** (time-
ordered, index-friendly), Alembic-managed. Repositories
([`infrastructure/db/repositories/`](../src/seedbank/infrastructure/db/repositories/))
are the only code that touches the ORM. Core entities:

- **Identity & auth**: `users`, `refresh_tokens`, `oauth_accounts`, `api_keys`,
  audit log.
- **Reference / catalog**: `seed_types`, `suppliers`.
- **Inference graph** (the traceability chain):
  - `scan_batches` — one per `POST /analyze`; carries the **state machine**
    (`pending → running → succeeded / partial / failed`), image count, duration,
    optional geo metadata.
  - `scan_images` — the uploaded images of a batch (stored in MinIO).
  - `inferences` — one model run over an image: `backend`, `model_id`,
    `latency_ms`, optional `error`.
  - `seed_detections` — one per detected seed: normalized bbox
    (`box_x_norm/y_norm/w_norm/h_norm`), `confidence`, `quality`
    (`good`/`bad`/null), `seed_type_id`, linked to its `inference`.
- **ML platform**: `model_artifacts` (registered weights + metadata + lifecycle
  status), `traffic_splits` (weighted routing), `datasets` + dataset items,
  `experiments`.

### 4.7 ML platform

- **Model registry** ([`infrastructure/ml/registry.py`](../src/seedbank/infrastructure/ml/registry.py),
  `services/model_registry_service.py`) — weights are uploaded to MinIO and
  recorded in `model_artifacts` (via `scripts/register_model.py` or `POST
  /models`). Each model has a **`builder_key`** that maps to a Python builder that
  constructs the right architecture before loading the weights.
- **Lifecycle** — `registered → staging → production → archived`. Promotion is an
  API action.
- **Backends** ([`infrastructure/ml/backends/`](../src/seedbank/infrastructure/ml/backends/)) —
  pluggable inference engines behind a common `base` interface:
  - `torch_local` — local PyTorch weights (the default).
  - `ultralytics_yolo` — YOLO detection.
  - `roboflow` — hosted Roboflow models.
- **Builders** ([`infrastructure/ml/builders/`](../src/seedbank/infrastructure/ml/builders/)) —
  architecture factories, e.g. `faster_rcnn_combined_v1` (detection),
  `resnet18_cbam_coffee_v3` / `resnet18_cbam_maize_v4` (CBAM-attention
  classifiers).
- **Model manager** ([`infrastructure/ml/manager.py`](../src/seedbank/infrastructure/ml/manager.py)) —
  loads/caches model instances in the worker process so weights aren't reloaded
  per request.
- **Traffic router** ([`services/traffic_router.py`](../src/seedbank/services/traffic_router.py)) —
  chooses which production model serves a given request using weighted
  `traffic_splits` (A/B testing). `ai_developer`/`admin` can override with an
  explicit `model_id` at analyze time.

### 4.8 Inference pipeline (the core flow)

```
POST /api/v1/analyze  (multipart: files[] + optional seed_type_id/supplier_id/
                       model_id/country_code/gps)
        │  validate (count/size/MIME), store images → MinIO,
        │  create scan_batch (pending) + scan_images, enqueue Celery task
        ▼
Celery  worker-inference  (queue: inference)
        │  batch → running (compare-and-set state machine)
        │  for each image:
        │     traffic router picks the model (or honors override)
        │     DETECT  → bounding boxes per seed   (detection model)
        │     for each detected crop:
        │        CLASSIFY → good/bad + confidence  (classification model)
        │     persist inference + seed_detections (full traceability)
        ▼
        batch → succeeded / partial / failed   (partial = some images errored)
        │  (DWH dual-write to ClickHouse, if enabled)
        ▼
GET /api/v1/batches/{id}   ← clients poll every ~2s until terminal
```

The two ML stages live in
[`infrastructure/ml/pipeline/`](../src/seedbank/infrastructure/ml/pipeline/)
(`detect.py`, `classify.py`, `factory.py`); the worker task is
[`workers/tasks/analyze.py`](../src/seedbank/workers/tasks/analyze.py). The batch
state machine uses compare-and-set updates so concurrent workers can't corrupt
state. Image upload is **multipart only** today (presigned-upload was scoped but
not built).

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
Redis is broker (DB 1) and result backend (DB 2). Queues:

- **`inference`** — `worker-inference` container; runs the detect→classify
  pipeline. This is the GPU/CPU-heavy worker that loads model weights.
- **default / cpu** — `worker-cpu` container; runs DWH dual-write and experiment
  evaluation.
- (`housekeeping` queue is declared but has no task yet.)

`celery_task_always_eager` makes tasks run inline in tests.

### 4.12 Observability

Structured JSON logging (structlog, every line carries `request_id`),
Prometheus `/metrics`, OpenTelemetry tracing (opt-in via env), Sentry error/
performance monitoring (opt-in via DSN), and the `/healthz` + `/readyz` probes.

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

### 7.1 Docker Compose services (dev: `compose.yaml`)

The whole stack runs with Docker Compose. Containers (host-published ports as
configured locally):

| Service (`container_name`) | Purpose | Notable port |
|---|---|---|
| `seedbank-api` | FastAPI app | `8000` |
| `seedbank-worker-inference` | Celery worker, `inference` queue (detect→classify) | — |
| `seedbank-worker-cpu` | Celery worker, DWH + experiments | — |
| `seedbank-postgres` | OLTP database | `5442→5432` |
| `seedbank-redis` | Cache, Celery broker/result, rate limiter | `6379` |
| `seedbank-minio` | Object store (images, weights, datasets, experiment artifacts) | `9000`/`9001` |
| `seedbank-clickhouse` | Analytics warehouse | `8123` |
| `seedbank-mlflow` | Experiment tracking UI/server | `5000` |
| `seedbank-frontend` | Built web app served by nginx | `5173→80` |
| `seedbank-adminer` | Postgres admin UI | — |
| `seedbank-ch-ui` | ClickHouse admin UI | — |
| `seedbank-prometheus` / `seedbank-grafana` | Metrics + dashboards | — |

> **Note on CORS for local dev:** the API only allows the origins in
> `CORS_ALLOW_ORIGINS` (default `http://localhost:5173`). The dockerized
> `seedbank-frontend` serves the **built** web app on `5173`. To run the Vite dev
> server (hot reload) against the live API, either serve it on `5173` (stop the
> frontend container) or add your dev origin to `CORS_ALLOW_ORIGINS` and restart
> the `api` service.

### 7.2 Makefile workflows

The [`Makefile`](../Makefile) is the developer entrypoint. Common targets:

| Target | Does |
|---|---|
| `make up` / `make up-dev` | Bring up the stack (dev) |
| `make up-infra` | Just the datastores (Postgres/Redis/MinIO/ClickHouse) |
| `make up-no-inference` | Stack without the heavy inference worker |
| `make up-obs` / `make up-front` | Add observability / frontend |
| `make migrate` / `make migrate-clickhouse` | Run Postgres / ClickHouse migrations |
| `make seed` | Seed reference + dev data (`scripts/seed_dev.py`) |
| `make check` | `fmt` + `lint` + `typecheck` (ruff + mypy) |
| `make test` / `test-unit` / `test-integration` / `test-e2e` | Test pyramid |
| `make smoke` | End-to-end smoke (`scripts/smoke.sh`) |
| `make up-prod` / `down-prod` | Production overlay (`compose.prod.yaml`) |

### 7.3 Migrations, secrets, model registration

- **Postgres** — Alembic under `alembic/`; `make migrate`.
- **ClickHouse** — `make migrate-clickhouse`.
- **Secrets** — dev uses `.env`; prod uses **file secrets** under `/run/secrets`
  (one file per `Settings` field) via `compose.prod.yaml` + `secrets/`.
- **Model weights** — **not in git** (history was scrubbed to purge ~165 MB of
  `.pth`). MinIO is the source of truth; register with
  `scripts/register_model.py` or `POST /models`. The app won't infer without
  registered weights.

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

- **Backend** — pytest pyramid (`unit`/`integration`/`e2e`) via `make test*`;
  `make check` runs ruff + mypy; pre-commit runs ruff/mypy/gitleaks. (Caveats:
  integration tests are **not fully hermetic** — some boot the app and reach for
  a live Redis; see [`docs/revamp-status.md`](./revamp-status.md).)
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
| Web app | [`frontend/src/`](../frontend/src/) · [`frontend/README.md`](../frontend/README.md) |
| Web localization | [`frontend/src/i18n/`](../frontend/src/i18n/) |
| Mobile app | [`mobile/`](../mobile/) · [`mobile/README.md`](../mobile/README.md) |
| Backend status & roadmap | [`docs/revamp-status.md`](./revamp-status.md) |
| Operations runbook | [`docs/operations.md`](./operations.md) |
| Architecture diagrams | [`docs/diagrams/`](./diagrams/) |
| Architecture decisions | [`docs/adr/`](./adr/) |
```
