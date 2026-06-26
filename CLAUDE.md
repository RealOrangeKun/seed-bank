# Seed-Bank — Claude Project Guide

Loaded automatically into every Claude Code session in this repo. It is the
source of truth for how we build, test, and ship. Keep it short — depth lives
in `docs/` and in the skills. Nested `CLAUDE.md` files under `frontend/` and
`mobile/` load on demand when you work in those trees.

---

## What this repo is

Seed quality analysis platform: point a camera at a batch of seeds and get a
good/bad breakdown, powered by an ML pipeline (detection + quality
classification, model registry, A/B traffic splits, experiments). Four active
surfaces — all in scope:

| Surface | Path | What it is |
|---|---|---|
| **Backend** | `src/seedbank/` | Async FastAPI — auth, ML platform, inference, DWH, observability |
| **Frontend** | `frontend/` | React + Vite SPA — farmer + admin/ML-platform UIs, full EN/AR + RTL |
| **Mobile** | `mobile/` | Expo / React Native — camera capture → analyze → results |
| **ML pipeline** | `src/seedbank/infrastructure/ml/` | Registry, backends, detect/classify orchestrators |

The old prototype is archived (referenced for history only). Don't import from
it or patch it to fix prod — port the needed piece into the live surface and
delete the archived copy.

---

## Stack pillars (non-negotiable)

1. **Async end-to-end.** FastAPI + SQLAlchemy 2.0 `AsyncSession` + `asyncpg` +
   `httpx.AsyncClient` + `miniopy-async`. No sync DB calls in request paths.
   Sync code is allowed only inside Celery workers and CLI scripts.
2. **Layered architecture (hexagonal-lite).**
   `routers (api/) → services/ → repositories (infrastructure/db/) → ORM`.
   Routers never import SQLAlchemy; services never import FastAPI; domain
   entities (`domain/`) never import any framework. The boundaries are what
   keep each layer unit-testable in isolation.
3. **Pydantic at the boundaries.** Every request and response is a Pydantic v2
   schema in `schemas/`. Domain entities stay plain dataclasses.
4. **Config from env only.** All configuration flows through one
   `Settings(BaseSettings)` in `core/config.py`. No string literals for URLs,
   credentials, paths, thresholds, or feature flags — so deploys differ by env,
   not by code.
5. **Every model, every detection traceable.** `seed_detections.inference_id →
   inferences.model_id` (NOT NULL). If you can't tell which model produced a
   result, the design is wrong.

If a change you're about to make violates one of these, stop and re-plan.

---

## Repo map

```
src/seedbank/
  main.py              # FastAPI app factory
  api/
    deps.py            # current_user, require_role, db, redis, minio
    middleware.py      # request_id + structured logging, CORS
    errors.py          # DomainError → RFC 9457 Problem Details
    rate_limit.py
    v1/<feature>.py    # one router per feature, prefix /api/v1 (12 routers)
  core/                # config, ids, exceptions, logging, metrics, security, sentry, tracing
  domain/              # framework-free entities & value objects
  services/            # <feature>_service.py — use cases owning the transaction
  infrastructure/
    db/                # session, models.py, repositories/
    storage/           # minio_client.py (miniopy-async)
    analytics/         # clickhouse_client.py
    mlflow/            # MLflow client
    ml/                # registry, manager, builders/, backends/, pipeline/
  workers/             # celery_app.py, runtime.py, tasks/{analyze,dwh,experiment}.py
  schemas/             # Pydantic v2 DTOs (common.py: Envelope[T], Page[T])
  bootstrap/

tests/                 # unit / integration / e2e / load + factories; conftest = testcontainers
scripts/               # seed_dev.py, register_model.py, run_experiment.py, provision_smoke_model.py
alembic/versions/      # one migration per change; never edit applied ones
docs/                  # operations, revamp-status, system-overview, adr/
frontend/  mobile/      # web + mobile clients (own CLAUDE.md each)
models/                # only the .pth files — uploaded to MinIO at bootstrap
```

The 12 v1 routers: `auth, users, api_keys, models, traffic, analyze, batches,
analytics, shared, catalog, datasets, experiments`.

---

## Golden paths (each has a skill — invoke it)

- **Add an HTTP endpoint / feature module** → `add-endpoint` skill (or
  `/scaffold-feature <name>` then implement the service). Router does only
  parse → call service → return.
- **Add an ML model** → `add-model` skill. Drop the arch in
  `infrastructure/ml/builders/`, upload weights via `scripts/register_model.py`,
  promote with `PATCH /api/v1/models/{id}`. No service/router edits.
- **Run an experiment** → `run-experiment` skill. Offline eval vs a frozen
  dataset, read metrics, decide promotion.
- **Database migration** → `db-migration` skill (or `/new-migration "<msg>"`).
  Read the generated file; autogenerate is a starting point, not the answer.
- **Frontend work** → see `frontend/CLAUDE.md`.
- **Mobile work** → see `mobile/CLAUDE.md`.
- **Keep the FE/mobile API client in sync with the backend contract** →
  `api-contract` skill.

The analyze pipeline needs a promoted detection model, or it fails with
`ModelNotReadyError`. When a fixture model is missing, provision the tiny smoke
detector — see [known issues: analyze needs a model](.claude/memory/known-issues.md#analyze-needs-a-promoted-detection-model).

---

## Conventions that trip you up

- **UUIDv7 PKs everywhere.** Use `uuid7()` from `core/ids.py`, never `uuid4` —
  sortable, indexable, distributed-friendly.
- **Confidence is `Numeric(5,4)`**, bounding boxes are stored normalized 0–1 as
  `Numeric(7,6)`. Multiply by image size at render time; never store pixel
  coords as the source of truth.
- **Soft delete only on user-visible aggregates** (`scan_batches`, `datasets`,
  `users`). Internal tables hard-delete with `ON DELETE CASCADE`.
- **Errors are domain-first.** Services raise `DomainError` subclasses from
  `core/exceptions.py` (`NotFoundError`, `ConflictError`, `ValidationError`,
  `AuthError`, `ForbiddenError`, `RateLimitError`, `ExternalServiceError`,
  `ModelNotReadyError`) — never `HTTPException`. `api/errors.py` maps them to
  RFC 9457 `application/problem+json` so clients get one stable error shape.
- **Responses are enveloped.** Return `Envelope[T]` (single) or `Page[T]`
  (paginated) from `schemas/common.py`; inputs use `STRICT_INPUT`
  (`extra='forbid'`). Only `/healthz /readyz /metrics` skip the envelope.
- **Logging is structured.** `log.info("user.login", user_id=..., ip=...)` with
  dotted lowercase event names — searchable, unlike an f-string. `request_id`
  and `user_id` are auto-bound by middleware.
- **No bare `except:`.** Name the exception and either re-raise a domain error
  or log with stacktrace. Catching `Exception` to hide a bug is not allowed.
- **The service owns the transaction** (`async with session.begin()`);
  repositories return domain entities, not ORM rows; use `selectinload` to
  avoid N+1. Tests never mock `AsyncSession`, MinIO, or ClickHouse — use
  testcontainers.

---

## Workflow

Loop: **open an issue → branch → commit → PR that closes it → merge.**

- **Branches:** `<type>/<slug>` (e.g. `fix/supplier-refresh`, `feat/big-features`).
- **Commits:** Conventional Commits with scope —
  `feat(frontend):`, `fix(models):`, `docs(...)`, `test(dwh):`, `ci:`, `chore:`.
  Imperative, lower-case subject.
- **PR body:** `## What` (bullets, each ending `(Closes #N)` where relevant),
  optional `## Not included`, `## Test` (what you ran).
- **CI gates:** `check` + `test` on every PR/master; `build` + `smoke` on master
  — details in [CI gates](.claude/memory/workflow.md#ci-gates). The `/new-issue`
  and `/open-pr` commands drive this loop; see [the change
  loop](.claude/memory/workflow.md#the-change-loop).

Roles are `end_user / ai_developer / admin`. Per-request model override on
`POST /api/v1/analyze` is `ai_developer` + `admin` only.

---

## What NOT to do

- Don't hardcode credentials, model paths, thresholds, or URLs — they go in `Settings`.
- Don't add a new `analyze` endpoint variant. Extend the unified one.
- Don't add denormalized aggregate columns. Aggregates live in views or ClickHouse.
- Don't import from the archived prototype.
- Don't catch `Exception` to hide a bug, or write a sync DB call in an async handler.
- Don't ship a feature without request/response schemas and at least one e2e test.

---

## Where to look when you're stuck

- Team memory (conventions, locked decisions, gotchas) — @.claude/memory/MEMORY.md
  (the always-loaded index; open the type file whose subject matches your task)
- Roadmap + current revamp status — @docs/revamp-status.md
  (the original external plan was lost; this is the reconstructed source of truth)
- System overview (surfaces, data flow, ML platform) — @docs/system-overview.md
- Compose, healthchecks, observability, runbooks — @docs/operations.md
- Architecture decisions — @docs/adr/0001-frontend-backend-overhaul.md
- Frontend conventions — @frontend/CLAUDE.md · Mobile — @mobile/CLAUDE.md

When in doubt, read the existing tests for the closest feature — they show the
layered pattern in action.
