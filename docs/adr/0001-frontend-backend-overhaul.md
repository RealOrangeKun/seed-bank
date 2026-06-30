# ADR 0001 — Frontend + Backend Overhaul: kill UUID inputs, fix the catalog cascade, redesign dark mode

- **Status:** Accepted — partially implemented (P0 + P1 done; P3 mostly done; P2 + P4 still open). See [Status update — 2026-06-26](#status-update--2026-06-26).
- **Date:** 2026-06-21 (last verified against `master` on 2026-06-26)
- **Deciders:** Mohamed Amr (owner), with a verified read-only audit of the running app
- **Branch:** `feat/frontend` — this ADR's content and the P0/P1/P3 work now live on `master` (shipped in the v1.0.0 release)
- **Supersedes / relates to:** `docs/revamp-status.md` (overall revamp roadmap)

> **Read this first if you are picking up the work.** Sections
> [Current status](#current-status--what-is-done) and
> [Remaining work](#remaining-work--p2p3p4) are the handoff. Everything you need
> to continue — exact endpoints, files, and the already-written code to wire up —
> is there.

---

## Context and problem statement

The repo carries a production-grade async FastAPI service plus a React 18 + Vite
SPA (`frontend/`). The stack runs (API on `:58080`, Vite on `:5173`; demo users
seeded by `scripts/seed_dev.py`). The app *works*, but a walkthrough as
`admin@seedbank.dev` plus a 6-dimension read-only audit surfaced **53 confirmed
issues** (9 candidate issues were rejected by an adversarial pass). They cluster
into four themes:

1. **The UI leaks raw UUIDs into the UX and forces users to type them.**
2. **The dark theme is a flat, muddy monochrome** — surfaces are visually
   indistinguishable and several text/background pairs fail WCAG AA.
3. **Several backend capabilities have no UI** (datasets, OAuth, password change,
   experiment results, audit log, model config).
4. **Real backend correctness / architecture defects** (a layering violation,
   list endpoints that don't filter by actor, a missing `seed_type` relationship,
   inconsistent Pydantic strictness).

### The root-cause cascade (why this is not cosmetic)

The single defect that ties most issues together: the database has rich
reference data (`seed_types`, `suppliers`) and a model registry, but **there were
no listing endpoints to expose them**. The consequence chain:

```
no GET /seed-types, GET /suppliers
  → the analyze/models/experiments/traffic forms make users paste UUIDs
    → users never set a seed type (you can't type a UUID you don't know)
      → seed_detections.seed_type_id stays NULL
        → quality classification is ROUTED BY seed type (traffic_splits keyed on
          (kind, seed_type_id)) → no seed type → no classifier selected
          → detection quality stays NULL
```

This was observed live: a real 56-detection maize scan rendered every row as
"Seed type –", "Quality —". Fixing the catalog therefore unlocks **correct ML
results**, not just nicer dropdowns. This is the thesis the overhaul proves.

### Goal

A production-grade, accessible, self-explanatory app where **no user ever types a
UUID**, the dark theme keeps the agriculture identity but is actually usable,
every backend feature has a UI, and the backend honors the project's layered
architecture (see `CLAUDE.md`).

---

## Decision drivers

- The five non-negotiable stack pillars in `CLAUDE.md`: async end-to-end; layered
  `routers → services → repositories → ORM`; Pydantic at boundaries; all config
  via `core/config.Settings`; every detection traceable via
  `inferences.model_id`.
- "Production-grade bar" — no shortcuts that a reviewer would reject.
- The agriculture visual identity is good; only the **dark palette** is the
  problem (light mode was confirmed fine), so the redesign keeps the green
  identity and fixes contrast + elevation only.

## Decision

A **full, phased overhaul** of both tiers. Scope locked with the owner:

| Question | Decision |
|---|---|
| Scope | Full overhaul, **phased** (all 53 issues, P0→P4). |
| Suppliers | **Full supplier management** — CRUD endpoints + searchable selector. |
| Datasets | **Both** real image upload (presigned PUT + drag-drop) **and** build-from-existing-scans (AI engineers curate eval sets from real batches). |
| OAuth | **Wire Google/GitHub fully** (buttons always shown). If a provider's creds are missing, surface a **toast** instead of a dead button. Also add the missing password-change endpoint + UI. |

### Architecture principles upheld (do not regress these)

- Layered: routers never import SQLAlchemy; services never import FastAPI; domain
  entities import no framework. **Fix violations, don't add more.**
- Pydantic v2 at every boundary; UUIDv7 PKs via `core/ids.uuid7`; structured
  logging (`log.info("event.name", key=...)`); named exceptions (no bare
  `except`); async-only in request paths; testcontainers for integration tests.
- Every new endpoint ships with **1 unit** (service, mocked repo) + **1
  integration** (repo on real Postgres) + **1 e2e** (full HTTP path). Run
  `/check` before declaring done.
- Frontend: one feature module per resource (`features/<x>/{pages,api.ts}`),
  React Query + React Hook Form + Zod, the typed `openapi-fetch` client.
  **Regenerate `frontend/openapi.json` + `schema.d.ts` (`npm run gen:api`) after
  every backend change.**

---

## Phased roadmap

| Phase | Theme | Status |
|---|---|---|
| **P0** | Catalog & foundations (seed-type + supplier endpoints) — unblocks the UX work | ✅ Done |
| **P1** | Core UX: kill UUID inputs, redesign dark mode, fix visible bugs | ✅ Done |
| **P2** | Feature parity & new flows: datasets, OAuth + password change, experiment results, audit log, model config | ⬜ Open (only model config/metadata backend landed) |
| **P3** | Backend correctness & architecture hardening | ✅ Done (the last item — the `traffic.py` layer violation — was resolved by deleting that router entirely when the traffic-splits A/B feature was removed) |
| **P4** | Accessibility & responsive polish | 🟡 ~50% done |

P0 unblocks P1. Once P0/P1 are in, **P3 and P4 can proceed in parallel with P2**.

---

## Status update — 2026-06-26

Re-audited against the current `master`. The original work was authored on
`feat/frontend`; `master` has since shipped a **v1.0.0** release — bilingual
i18n/RTL web, a mobile app, an analytics dashboard, public share links, and batch
export/compare — **none of which are in this ADR's scope**. Net: **P0 and P1 are
fully landed and intact, most of P3 landed, and P2 + P4 are the genuine remaining
backlog** — they were leapfrogged by the v1.0.0 work.

### P3 — backend hardening: done

| Item | Status | Evidence |
|---|---|---|
| `SeedDetection.seed_type` relationship + label in `SeedDetectionOut` | ✅ Done | `infrastructure/db/models.py:699` (`relationship(lazy="selectin")`); `schemas/analysis.py:76` exposes a `SeedTypeRef`. |
| `seed_type` deduction in the worker | ✅ Done | `workers/tasks/analyze.py:448-457` — request `seed_type_id` wins, else the detector's class code maps to a `seed_type_id`. |
| Pydantic `extra="forbid"` on `*In` schemas | ✅ Done | shared `STRICT_INPUT` in `schemas/common.py`, applied across dataset/experiment inputs. |
| MinIO public endpoint | 🟡 Partial | `@field_validator` (rejects scheme/path/empty) + `minio_region` landed (`core/config.py`), but `minio_public_endpoint` still **defaults** to `localhost:9000`. |
| Authorization filter on list endpoints | 🟡 By design | `batches`/`api-keys` filter by actor; `experiments`/`datasets`/`models` are role-gated (ai_dev+) but not actor-filtered — currently intentional (AI-developer artefacts, not user data). |
| **Router imports ORM (layer violation)** | ✅ Done (by removal) | `api/v1/traffic.py` was the offender. The traffic-splits A/B feature was removed entirely (router, ORM model, schemas, and the `traffic_splits` table dropped in `0004_drop_traffic_mlflow`; `TrafficRouter` replaced by `services/model_resolver.py::ModelResolver`), so the violating router no longer exists. |

### P2 — feature parity: still open

Backend service/repo plumbing mostly exists; the **routes and UI do not**. All
flows reuse existing tables (`audit_log`, `experiment_results`, `dataset_items`,
`oauth_accounts`) — **no Alembic migration required**.

| Flow | Status | Note |
|---|---|---|
| Datasets presigned upload (`POST /datasets/{id}/upload-url`) + drag-drop UI | ❌ Open | `MinioStorage.presigned_put_url` exists (`storage/minio_client.py:95`); no route/UI. |
| Datasets build-from-batch (`POST /datasets/{id}/items/from-batch`) | ❌ Open | reuse the existing `add_items`; needs a `ScanImage` list + service method. |
| OAuth FE buttons + `/auth/callback` + `GET /auth/oauth/providers` | ❌ Open | login/callback routes already exist (`auth.py:165`/`184`); FE + a providers-discovery endpoint missing. |
| Password change (`POST /auth/password-change` + profile form) | ❌ Open | `auth_service.change_password` + `PasswordChangeIn` exist; no route/UI. |
| Experiment results (`GET /experiments/{id}/results` + table) | ❌ Open | `ExperimentResultRepository.list_for_experiment` exists; detail page still shows only the scalar `result_count`. |
| Audit-log read path (`GET /audit-log` + admin page) | ❌ Open | write path exists; no repository/service/router/page. |
| Model `config` / `training_metadata` | 🟡 Backend done | `ModelRegisterIn`/`ModelOut` carry both; FE surfacing pending. |

### P4 — accessibility & responsive: ~50%

- **Done:** badges carry text (not color-only), tables have an `overflow-auto`
  wrapper, theme-toggle + copy buttons have `aria-label`, `<main>` landmark,
  spinner `aria-hidden`.
- **Open:** keyboard-accessible rows (list rows use `onClick={navigate}`, not
  `<Link>`), `scope="col"` on `<th>`, a skip-to-content link, `CopyButton`
  clipboard `.catch()` + toast, pagination icon-button `aria-label`s, ARIA on the
  analyze "Optional metadata" accordion, and dialog form-reset-on-close
  (models + experiments).

### Known issues — updated

- **Tooling debt: resolved.** The ruff/mypy red-CI noted below was cleared; CI now
  runs green via `.github/workflows/{check,test,build,smoke}.yml`.
- **Blank-seed-type scans:** still routed via `(kind, seed_type_id)`, but the box
  is made runnable by `make provision-smoke-model` (registers + promotes a tiny
  detector to `production` so the `seed_type_id=None` fallback resolves), which CI
  runs before `make smoke`. The worker `seed_type` deduction (P3, above) also
  landed. **Verified 2026-06-26:** a no-seed-type analyze ran to `succeeded`.
- **Ops gotcha (found while verifying):** the `api` container does **not** run
  migrations on boot — only `make migrate` does. After a pull that adds a
  migration, the dev DB drifts until it's run (this caused a live `scan_batches`
  INSERT 500 on the later `share_token` migration `0002`). CI runs `make migrate`
  explicitly before smoke.

---

## Current status — what is done

### P0 — Catalog backend (commit `feat(catalog): …`)

New endpoints under `/api/v1`:

| Endpoint | Role | Notes |
|---|---|---|
| `GET /seed-types` | any auth | Backs every seed-type selector. |
| `GET /suppliers` | any auth | Lists global + the caller's own private suppliers; honors the soft-delete mixin. |
| `POST /suppliers` | ai_developer / admin | `is_global=true` is **admin-only**; otherwise private to the creator. |
| `PATCH /suppliers/{id}` | admin / owner | |
| `DELETE /suppliers/{id}` | admin / owner | Soft delete (`deleted_at`). |

Layered pieces, all in their correct homes:

- `src/seedbank/schemas/catalog.py` — `SeedTypeOut`, `SupplierOut`,
  `SupplierCreateIn`, `SupplierUpdateIn`.
- `src/seedbank/services/catalog_service.py` — `CatalogService`
  (`list_seed_types`, `list_suppliers(actor)`, `create_supplier`,
  `update_supplier`, `soft_delete_supplier`; `IntegrityError → ConflictError`).
- `src/seedbank/infrastructure/db/repositories/seed_type.py` —
  `SeedTypeRepository.list_all()`. (`SupplierRepository` already existed with
  `list_visible_to` / `get_visible`.)
- `src/seedbank/api/v1/catalog.py` — the router, wired in `api/v1/__init__.py`;
  service provided via `api/deps.py`.
- `src/seedbank/bootstrap/suppliers.py` + `scripts/seed_dev.py` — 3 demo global
  suppliers seeded idempotently (upsert on `slug`).

**Gotcha already fixed (do not reintroduce):** `SupplierOut` exposes the JSONB
column as `metadata`. It **must** use
`validation_alias="supplier_metadata"` + `serialization_alias="metadata"`. Do
**not** use `AliasChoices("metadata", "supplier_metadata")` — the `"metadata"`
choice resolves against SQLAlchemy's `Base.metadata` and 500s.

Verified over HTTP: seed-types list; supplier list/create; RBAC (end_user → 403,
ai_dev creating a global supplier → 403). Unit tests pass.

### P1 — Core UX

- **P1a — selectors (commit `feat(frontend): …`).** New
  `frontend/src/components/shared/resource-select.tsx` exports `SeedTypeSelect`,
  `SupplierSelect`, `ModelSelect` (props `kind`, `status?`), `DatasetSelect` —
  each a Radix `Select` backed by a list hook, emitting the UUID as the form
  value while showing a human label. `frontend/src/features/catalog/api.ts` adds
  `useSeedTypes()` / `useSuppliers()` (long `staleTime` — reference data). Every
  raw-UUID `<Input>` on analyze / models / experiments / traffic was replaced;
  Zod still validates a UUID under the hood. **No UUID typing anywhere.**
- **P1b — human labels.** Batch titles read `"Scan · <date>"`; scan-history and
  dashboard rows key on timestamp; the users table dropped its UUID column;
  experiment and batch rows resolve model & dataset IDs to names. UUIDs survive
  only as copy-to-clipboard affordances.
- **P1c — dark-mode redesign.** Reworked the `.dark` block in
  `frontend/src/styles/globals.css` with a real elevation ramp (canvas 9% →
  surface 12% → card 14% → popover), AA-contrast muted text, and a wheat/amber
  accent + an info hue so the UI isn't a single muddy green. New `surface` +
  `info` tokens mapped into `frontend/tailwind.config.ts`; the sidebar uses
  `bg-surface`. The light palette is untouched. Verified by computed-style
  contrast: muted text 8.2:1, foreground 15:1.
- **P1d — `image_count`.** `GET /batches` returned `image_count=0` (schema
  default) while the detail endpoint was correct. Fixed in the **repository**
  (`scan_batch.py`, correlated `COUNT` subquery — no N+1, no denormalized
  column) and mapped onto `BatchOut` in `batch_service.py`. Integration test
  asserts list count == detail count.

### Storage fix (commit `fix(storage): …`)

`minio_client.py`'s presign client points at `minio_public_endpoint` (the
browser-facing host), unreachable from inside the API container. Signing without
a known region triggered a live `GetBucketLocation` call → presign failed. Both
`Minio` clients now receive an explicit `minio_region` (new `Settings` field,
default `us-east-1`), so SigV4 signing happens **offline**.

---

## Remaining work — P2/P3/P4

> **Note (2026-06-26):** the sections below are the *original* handoff. For what
> has since landed vs. what is still open, see
> [Status update — 2026-06-26](#status-update--2026-06-26) — several P3 items here
> (the `seed_type` relationship, worker deduction, and `extra="forbid"`) are now
> **done**, and most of P2 is still open.

### P2 — Feature parity & new flows

**2a. Datasets become usable (two paths).**
- *Real upload:* add `POST /api/v1/datasets/{id}/upload-url` returning a
  presigned **PUT** URL (MinIO via `miniopy-async`, signed against
  `minio_public_endpoint`). Frontend: replace the storage-key textarea in
  `frontend/src/features/datasets/pages/dataset-detail-page.tsx` with a drag-drop
  uploader (reuse `frontend/src/components/shared/file-dropzone.tsx`) → request
  URL → PUT bytes → `POST /datasets/{id}/items` (already exists,
  `api/v1/datasets.py:84` `add_items`) with the returned key.
- *Build from scans (the genuinely useful curation flow for AI engineers):* add
  `POST /api/v1/datasets/{id}/items/from-batch` (service maps `ScanImage` +
  detections → `DatasetItemCreateIn` candidates with `ground_truth`). Frontend:
  an "Add to dataset" action on the batch detail page (ai_dev/admin) using
  `DatasetSelect`.

**2b. OAuth + password change.**
- The OAuth **backend already exists**: `GET /auth/oauth/{provider}/login`
  (`api/v1/auth.py:163`) and `GET /auth/oauth/{provider}/callback`
  (`api/v1/auth.py:181`). Remaining is **frontend only**: Google/GitHub buttons
  on `frontend/src/features/auth/pages/login-page.tsx` → redirect to the login
  route; add an `/auth/callback` route to capture the `TokenPair`. If a provider
  is not configured, the backend should return a clear 4xx and the UI shows a
  **toast** (per the locked decision) — add a tiny `GET /auth/oauth/providers`
  (or reuse the 4xx) so the UI knows what's enabled before redirecting.
- Password change: the service method **already exists** —
  `auth_service.change_password` (`src/seedbank/services/auth_service.py:339`,
  revokes tokens + writes an audit row). It has **no route**. Add
  `POST /api/v1/auth/password-change` (router only, validates `PasswordChangeIn`)
  and a change-password form on
  `frontend/src/features/profile/pages/profile-page.tsx`.

**2c. Remaining parity gaps.**
- `GET /api/v1/experiments/{id}/results` (paginated): the repo method
  **already exists** — `ExperimentResultRepository.list_for_experiment`
  (`src/seedbank/infrastructure/db/repositories/experiment.py:166`). Expose it +
  add a results table to
  `frontend/src/features/experiments/pages/experiment-detail-page.tsx` (today it
  shows only a scalar `result_count`).
- `GET /api/v1/audit-log` (admin, paginated, filterable) + a simple admin Audit
  page. The `audit_log` table exists (`infrastructure/db/models.py:200`) and is
  written to (traffic changes, password change) but has **no read path** — add a
  repository method + service + router.
- Surface model `config` / `training_metadata` in the register dialog + model
  detail (the schema supports them; the UI omits them).

### P3 — Backend correctness & architecture hardening

| Issue | Fix |
|---|---|
| **Router imports ORM** (layer violation flagged by the audit) | Push the ORM/query usage behind a repository method; the router calls the service only. Locate the exact offending import under `api/v1/`. |
| **Authorization gap on list endpoints** | Verify every list endpoint filters by actor (non-admin sees only their own rows); add the ownership filter + an e2e test where missing (`experiments.py`, `batches.py`, …). |
| **`SeedDetection.seed_type` relationship missing** | Add the SQLAlchemy relationship + FK navigation so detail responses resolve the seed-type **label**; expose `seed_type` (code/name) in `SeedDetectionOut` (`src/seedbank/schemas/analysis.py`). |
| **`seed_type` deduction** | In `src/seedbank/workers/tasks/analyze.py`, when a detection has no explicit seed type, fall back to the parent inference/model's `seed_type_id` so results aren't blank. |
| **MinIO public endpoint default** | `minio_public_endpoint` defaults to `localhost:9000`; make it fail-fast (`None` + `@field_validator`, or derive) and document in `.env.example`. |
| **Pydantic `extra="forbid"` inconsistency** | Add a shared `STRICT_INPUT = ConfigDict(extra="forbid")` to all `*In` schemas (dataset/experiment currently silently ignore typo'd fields). |

### P4 — Accessibility & responsive polish

- **Clickable rows → real links:** wrap batch/model/experiment/dataset/user table
  rows in `<Link>` so they're keyboard-focusable and open-in-new-tab works.
- **No color-only signaling:** add text/icon to `confidence-badge.tsx`,
  `status-badge.tsx`, and the `bbox-overlay.tsx` labels.
- **Tables on mobile:** horizontal-scroll containers with a card/stacked fallback
  at `sm`; fix the `users-page.tsx` overflow.
- **A11y basics:** `aria-label` on icon-only buttons (theme toggle, copy,
  pagination), `scope="col"` on `<th>`, a skip-to-content link, `aria-hidden` on
  the decorative logo, proper ARIA on the analyze "Optional metadata" accordion.
- **Robustness:** `ErrorState` gets a Retry wired to `query.refetch()`;
  `CopyButton` catches clipboard rejection (toast) with a ~2s reset; dialogs
  reset form state on close; the 404 page offers `useNavigate(-1)`.

### Minor P1 residuals

The traffic current-splits table and the batch-detail `ImageCard` still show a
short id (both have a copy button) — low priority.

---

## Consequences

### Positive

- The catalog cascade is broken at the root: selecting a seed type now flows all
  the way to a selected classifier and a populated `quality`.
- The dark theme is usable and keeps the green agriculture identity.
- New backend code follows the layered pattern and ships with the test triangle.

### Known issues & risks (read before continuing)

- **Pre-existing tooling debt — NOT introduced by this work.** _(Resolved
  2026-06-26 — CI is now green; see the [Status update](#status-update--2026-06-26).)_
  The committed tree
  does not pass `ruff check .` (~200 violations: TC001/TC003/PLC0415/…),
  `ruff format --check .`, or `mypy` under the pinned **ruff 0.15.18 / mypy
  1.20.2** — almost certainly the "pin deps" commit bumping tools without a
  re-lint. **CI is red independent of this overhaul.** New files here match
  surrounding patterns and pass `ruff format`. **Recommend a separate cleanup
  pass:** `ruff check --fix` for the autofixable bulk + a
  `runtime-evaluated-base-classes` config so Pydantic models stop tripping the
  typing-only-import rules.
- **Blank-seed-type scans currently fail.** _(Updated 2026-06-26 — now made
  runnable via `make provision-smoke-model`, plus the worker `seed_type`
  deduction landed; see the [Status update](#status-update--2026-06-26).)_ A scan
  submitted with **no** seed
  type raises `ModelNotReadyError: No production model and no traffic splits for
  kind=detection seed_type_id=None`. Cause: the seeded demo data only has
  detection traffic splits for specific seed types (coffee, maize), there is **no
  default-segment split**, and **no detection model is promoted to production**.
  This is a **demo-data / model-promotion state, not a regression** (no
  routing/worker/model code was touched). Close it by one of: promote a detection
  model + add a default split (P-ops); make the seed-type selector effectively
  required in the analyze UI; or surface the routing error clearly. Note this
  intersects with the P3 `seed_type` deduction item. The full pipeline is
  verified working **when a seed type is provided** (a maize scan produced 50
  detections, all quality-graded).
- **Dev convenience:** a source bind-mount for the `api` service lives in
  `compose.override.yaml` (gitignored) so backend edits hot-reload without a
  rebuild. It is intentionally not committed.

---

## How to continue

### Workflow

1. **Per backend change:** edit the model → `/new-migration "<msg>"` if the schema
   changed → **read the generated migration** → `/check` (ruff + mypy + fast unit)
   → `make test` for the new unit/integration/e2e. Then **regenerate the frontend
   client**: with the API running, `npm run gen:api` (updates `openapi.json` +
   `schema.d.ts`) and commit the regenerated files alongside the backend change.
2. **Per frontend change:** the Vite dev server is on `:5173`. Reload/navigate to
   the changed route, check the console for errors and the network tab for API
   calls, screenshot the visual change, and (for dark mode) assert contrast on
   text/badges/surfaces. Resize to mobile to confirm tables/sidebar. Confirm the
   a11y tree exposes labelled fields/links.

### End-to-end smoke test (proves the thesis)

Log in → **New analysis** → pick a **seed type from the dropdown** (no UUID) +
upload a maize image → open the batch → detections show a **seed-type label and
quality** (not "–"/"—") → scan history shows the real **image count** and a human
title → toggle dark mode and confirm cards/sidebar visibly separate from the
canvas.

### Conventions that will trip you up

- UUIDv7 PKs via `core/ids.uuid7` (never `uuid4`). Confidence is `NUMERIC(5,4)`.
  Bounding boxes stored normalized (0–1). Soft delete only on user-visible
  aggregates. See `CLAUDE.md` for the full list.
- Demo users (from `scripts/seed_dev.py`): `admin@seedbank.dev / AdminDemo123!`,
  `ai-dev@seedbank.dev / AiDevDemo123!`, `user@seedbank.dev / UserDemo123!`.
- Switching the production model is a promotion via `PATCH /api/v1/models/{id}`
  (the `ModelResolver` then resolves it) — **no code change**. There is no A/B /
  `traffic_splits` mechanism anymore.
