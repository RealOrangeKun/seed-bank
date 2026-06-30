# Revamp Status

Living record of the prototype → production-grade revamp. This is the durable,
in-repo replacement for the working plan file that drove the revamp and was lost.

> **Reconstructed 2026-06-20** from git history, `docs/`, `CLAUDE.md`, and the
> code itself. The revamp ran **2026-04-08 → 2026-05-03** and has been paused
> since. `master` is the tip — there is no in-progress work on another branch
> (`persistence` is the archived Jan-2026 prototype; `master` is 67 ahead / 0
> behind it). A `git filter-branch` rewrite on 2026-05-02/03 scrubbed history
> (safety copy: `backup/pre-rewrite-1777693267`), almost certainly to purge the
> 165 MB `.pth` weights.

## Phase status

| Phase | Scope | Status |
|---|---|---|
| 1 — Scaffold | FastAPI app factory; prototype archived to `legacy/` | ✅ done |
| 2 — Schema | 18-table async SQLAlchemy + Alembic baseline; UUIDv7 PKs (now **17** — `traffic_splits` dropped in `0004_drop_traffic_mlflow`) | ✅ done |
| 3 — Infra | repositories + clients + lifespan + `/readyz` | ✅ done |
| 4 — Auth | email/pw + OAuth + RBAC + rate limiting | ✅ done |
| 5 — ML platform | registry, 3 backends, model manager, `ModelResolver`, `/models` | ✅ done (weighted-A/B traffic-splits **removed**; `TrafficRouter` replaced by `ModelResolver` — production-model resolution with a global fallback, no A/B) |
| 6 — Inference path | unified `POST /analyze` + Celery batch + detect/classify | ✅ done¹ |
| 7 — Experiments | datasets, experiment runner | ✅ done² (runs **without MLflow** — MLflow tracking removed; metrics live in Postgres + a MinIO Markdown report) |
| 8 — DWH | OLTP → ClickHouse | ✅ done as **app-level dual-write** (true logical-replication CDC deferred; `wal_level=logical` set but unused) |
| 9 — Observability | `/metrics` + OTel + Sentry | ✅ wired, **opt-in** (not default-on) |
| 10 — Load tests / full e2e / docs polish | the original Phase-10 deliverables | ❌ **not done** |

The commits tagged "Phase 10" delivered a **production-hardening sprint** (prod
compose overlay, file secrets, worker process-loop fixes, `seed_dev.py`,
bootstrap extraction, smoke script, env-driven config) — valuable, but a
different body of work than the *planned* Phase 10. The planned Phase 10 (load
tests, comprehensive coverage, docs polish) was never started, and **CI/CD was
never scoped**. That is the unfinished tail of the revamp.

¹ Multipart upload only — the presigned-upload endpoint and batch cancellation
("Phase 6.5") were never built.
² Works, but `scripts/run_experiment.py` (referenced in `CLAUDE.md`/README) does
not exist.

## What the system does today

All of the following work on `master`:

- **Auth** — register/verify/login/refresh/logout, refresh-token rotation with
  replay detection, Google OAuth,
  RBAC (`admin`/`ai_developer`/`end_user`), per-route rate limiting, append-only
  audit log, one-shot bootstrap-admin.
- **Model lifecycle** — register weights to MinIO + `model_artifacts`
  (`scripts/register_model.py` + `POST /models`), promote
  `registered→staging→production→archived`; `ModelResolver` resolves the
  `production` model for a `(kind, seed_type_id)` segment with a global fallback
  (no A/B / traffic-splits), per-request `model_id` override for
  `ai_developer`/`admin`.
- **Inference** — `POST /analyze` → MinIO + Postgres → Celery `analyze_image` →
  production-model resolve (`ModelResolver`) → detect → classify-per-crop →
  persist `inferences` + `seed_detections` with full `detection→inference→model`
  traceability → CAS batch state machine
  (`pending→running→succeeded/partial/failed`) → poll `GET /batches/{id}`.
- **Experiments** — datasets + items, `POST /experiments` → offline-eval runner →
  metrics persisted to Postgres (`summary_metrics` / `experiment_results` /
  `model_metrics`) + Markdown report to MinIO (no MLflow) →
  `GET /models/{id}/performance`.
- **DWH** — Celery dual-write to ClickHouse star schema (3 `dim_*` + 4 `fact_*`,
  `ReplacingMergeTree`, partition-by-month).
- **Ops** — dev + prod compose stacks, 7-target multi-stage Dockerfile,
  `/healthz` + `/readyz`, `/metrics`, OTel, Sentry, structured logging, RFC 9457
  errors, env-only `Settings` with `secrets_dir`, smoke test, pre-commit
  (ruff/mypy/gitleaks).

The five stack pillars (async end-to-end; layered routers→services→repos→ORM;
Pydantic boundaries; central `Settings`; model traceability) are enforced. A
stub/TODO scan over ~13.6k LOC found 3 benign documented TODOs and zero
`NotImplementedError` stubs.

## What's left

**P0 — close the revamp tail**
- **No CI/CD** — no `.github/workflows/`, despite `CLAUDE.md` promising "CI runs
  the same."
- **`scripts/run_experiment.py` missing** — referenced in `CLAUDE.md`/README;
  blocks the documented offline-eval workflow.
- **Planned Phase 10 undone** — `tests/load/` empty; true coverage unknown (the
  committed `coverage.xml` is a partial `make check` artifact, not the full
  pyramid — routers/services read 0% there only because e2e/integration weren't
  in that run).

**P1 — production-readiness**
- Coverage holes: worker tasks (`analyze.py`, `experiment.py`) and ML backends
  (`torch_local`/`yolo`/`roboflow`) barely/never exercised; MinIO storage and
  full OAuth callback mocked everywhere.
- `housekeeping` queue declared but has no task (no retention/cleanup, no Celery
  beat).
- ~~No `TrafficSplitRepository`~~ — **moot:** the traffic-splits A/B feature was
  removed (`TrafficRouter` deleted, replaced by `ModelResolver`; `traffic_splits`
  dropped in `0004_drop_traffic_mlflow`), so there is no split query to push
  behind a repository.
- Endpoints whose service/schema already exist but no route: password change
  (`PATCH /users/me/password`), `GET /experiments/{id}/results`, presigned upload.
- **Test suite not hermetic** (confirmed 2026-06-20): app-booting integration
  tests fail outside Docker because the rate limiter dials `redis:6379` and
  `fakeredis` doesn't cover it. Make `app_client` use fakeredis end-to-end (or
  add a redis service to `test.yml`) before the coverage gate can be trusted.
- **No dependency lockfile** — add `uv.lock` (or pinned constraints) so installs
  and CI are reproducible.

**P2 — hardening / correctness / docs**
- Validate `builder_key` at model-register time (else opaque 503 at inference).
- Roboflow `classify` fallback fragile; OAuth provider tokens fetched then
  discarded (encrypted columns unused).
- Workers don't propagate `request_id`/`user_id` → logs lack request correlation.
- OTel SQLAlchemy/Redis statement sanitization pending a library upgrade.
- Stale docs: this used to be only the README §Status; `CLAUDE.md`'s "Where to
  look" table still points at `docs/architecture.md`, `docs/auth.md`,
  `docs/ml-platform.md`, `docs/dwh.md` which don't exist (content lives in
  `docs/diagrams/`); dual-write-vs-CDC decision undocumented.
- `AuditLog` is write-only (no read repository); single Alembic migration, so the
  ALTER/rollback path is untested.

**Confirmed non-issue:** the confusion-matrix math in
`services/eval/classification.py` is correct — keys are
`f"{ground_truth}_pred_{pred}"`, so `fn_bad = confusion["bad_pred_good"]` is
right.

### Verified suite state (2026-06-20, fresh Python 3.12 toolchain)

- **Unit tier: 171 passed** after fixing two suite-rot bugs the missing CI never
  caught — a stale `_init_obs_per_worker` assertion (code renamed it to
  `_init_per_worker`), and a `worker_process_init` test that leaked the global
  `runtime._LOOP` into the `dwh_helpers` tests. Both fixed + committed.
- **Integration tier: 24 passed / 13 failed — and the failures are not product
  bugs.** Every failing test boots the full `app_client`, whose slowapi rate
  limiter connects to the compose hostname `redis:6379` (unreachable outside
  Docker); the `fakeredis` fixture doesn't intercept the limiter's client. Pure
  Postgres-testcontainer repository tests pass. The suite is **not hermetic**.
- **No dependency lockfile** — a fresh install pulls newer-than-May libs
  (starlette 1.3, redis 5.3, clickhouse-connect 0.15…), so builds aren't
  reproducible and deprecation drift (`HTTP_422_UNPROCESSABLE_ENTITY`) is already
  visible.
- The committed `coverage.xml` (~15%, May 2) is a partial `make check` artifact —
  ignore it. A clean coverage number must come from a hermetic run in CI.

## Resume roadmap

Sequenced **original-Phase-10 first** (the agreed first track):

1. **Make the suite hermetic, then establish true coverage** — fix the
   `app_client`/rate-limiter Redis dependency (fakeredis end-to-end or a CI redis
   service) and add a dependency lockfile; only then is `make test` coverage
   meaningful. (Unit tier already green: 171 passed.)
2. **Add CI** under `.github/workflows/`: `check.yml` (mirror `make check`),
   `test.yml` (full pyramid), `smoke.yml` (compose up → `make seed` →
   `scripts/smoke.sh`), `build.yml` (multi-stage images; assert no torch in the
   api image).
3. **Close worst coverage holes** — worker-task tests (`analyze`/`experiment`
   with real Postgres + stubbed backend), ML-backend tests, MinIO storage
   integration, OAuth callback integration.
4. **Add `tests/load/`** — concurrent `POST /analyze`, batch-state consistency,
   DWH dispatch lag (Locust or k6).
5. **Docs polish** — create the four missing `docs/*.md` (or repoint to
   diagrams); document the dual-write-vs-CDC decision.

Then fold in the near-term P0/P1: `scripts/run_experiment.py`, the
`housekeeping` task + Celery beat, and the three already-backed endpoints.

## Open questions to confirm
- Was the `git filter-branch` rewrite the `.pth` purge, and are `models/*.pth`
  now MinIO-only (not re-added to git)?
- `models/` holds 5 `.pth` files but only 3 are wired to builders
  (combined-faster-rcnn, coffee-v3, maize-v4); are
  `FasterRCNN_ResNet50_Final.pth` and `ResNet50_maize_seeds_NEW.pth` obsolete?
