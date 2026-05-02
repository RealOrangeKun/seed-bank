# Operations

How to run the stack locally, what each service does, what the
healthchecks mean, and how to debug a sick stack.

## TL;DR — running locally

First time on a fresh checkout:

```bash
make env            # creates .env from .env.example (idempotent)
make up-infra       # postgres + redis + minio + clickhouse only — no build, ~10s
make up             # full stack (builds api image first time, ~5–10 min)
make up-obs         # full stack PLUS prometheus + grafana (obs profile)
make logs           # follow logs
make down           # stop containers (volumes survive)
make down-volumes   # wipe volumes too — total reset
```

`make help` lists every target.

## Port conflicts on shared dev machines

If another stack on the host is already bound to 5432 / 6379 / 8000 etc.,
drop a `compose.override.yaml` next to `compose.yaml`. It is auto-loaded
by Compose and is gitignored. Example shifts everything by 50000:

```yaml
services:
  postgres:
    ports: !override
      - "127.0.0.1:55432:5432"
  redis:
    ports: !override
      - "127.0.0.1:56379:6379"
  api:
    ports: !override
      - "127.0.0.1:58080:8000"
```

`!override` is required (compose 2.20+); without it Compose appends to
the existing `ports` list and the original bindings still apply.

When the api port shifts, set `API_PORT=58080 make wait` (or export it)
so `make wait` polls the right address.

## The lean stack — what each container does

| Service | Image | Purpose |
|---|---|---|
| `api` | `seedbank/api:0.1.0` (CPU-only, no torch) | HTTP entrypoint |
| `worker-cpu` | same image as `api` | Celery worker for cdc + housekeeping (Phase 6+) |
| `worker-inference` | `seedbank/worker-inference:0.1.0` (CUDA) | Celery worker for analyze + evaluation. Opt-in via `--profile gpu` |
| `postgres` | `postgres:16-alpine` | OLTP system of record. `wal_level=logical` preconfigured |
| `redis` | `redis:7-alpine` | Cache + Celery broker + rate-limit backend |
| `minio` | `minio:RELEASE.2024-11-07` | Object storage (images, models, experiments, datasets) |
| `clickhouse` | `clickhouse-server:24.10-alpine` | Analytics warehouse (Phase 8) |
| `mlflow` | `ghcr.io/mlflow/mlflow:v2.18.0` | Experiment tracking + model registry mirror |
| `adminer` | `adminer:4.8.1` | Web SQL UI. Opt-in via `--profile dev` |

Resource caps live in `compose.yaml`. The full lean stack fits in
roughly 3.5 GB RAM at idle.

## Healthchecks

- `postgres` — `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB`
- `redis` — `redis-cli ping`
- `minio` — HTTP GET `/minio/health/live`
- `clickhouse` — HTTP GET `127.0.0.1:8123/ping` (note: not `localhost`,
  alpine resolves that to ::1 first and CH binds IPv4 only)
- `mlflow` — HTTP GET `/health`
- `api` — HTTP GET `/readyz`

`/healthz` answers up/down for the process. `/readyz` probes every
backend dependency and returns a per-component status — read its body
when something is degraded:

```json
{"status": "degraded",
 "checks": {"postgres":"ok","redis":"ok","minio":"ok","clickhouse":"down: ..."}}
```

## Migrations

```bash
make migrate         # alembic upgrade head against the running api container
make migrate-down    # rollback one revision
```

After the first `make up`, run `make migrate` once. The schema is
non-destructive on re-runs (Alembic is idempotent at `head`).

## Logs and debugging

```bash
make logs                    # all services
docker compose logs -f api   # one service
docker compose exec postgres psql -U seedbank -d seedbank
docker compose exec redis redis-cli
```

The api emits structured JSON logs in `ENV=prod` and pretty console
logs in `ENV=dev`. Every line carries `request_id` + `user_id` when
inside a request.

## Wiping state

```bash
make down-volumes
docker volume prune -f
```

Removes every persistent volume (postgres data, minio buckets,
clickhouse data, redis dump). Use when a migration goes sideways and
you want a known-clean slate.

## Common failures

- **Port already allocated**: another stack is on the same port —
  add `compose.override.yaml`.
- **Postgres: relation already exists**: leftover state from a previous
  run — `make down-volumes` and try again.
- **Api unhealthy with clickhouse: down**: clickhouse takes 15–20 s to
  warm up; the api healthcheck has a 30 s `start_period`. Wait, then
  re-curl `/readyz`. If still down, `docker compose logs clickhouse`.
- **Worker-cpu crashlooping with `ModuleNotFoundError: seedbank.workers.celery_app`**:
  this is expected until Phase 6 lands. The worker image is
  built but the celery entrypoint hasn't been written yet. `make up`
  starts only api + infra to keep the smoke clean.

## Observability (Phase 9)

The app exposes three signals end-to-end: **metrics**, **traces**, and
**errors**. Each is opt-in at the infrastructure layer; the application
side is always wired so deploying a collector is the only switch.

### Metrics — Prometheus

The API serves Prometheus text on `GET /metrics` (excluded from the
HTTP middleware so scrapes do not dominate the histograms). Core
metrics:

| Metric | Kind | Labels |
|---|---|---|
| `http_requests_total` | counter | `method`, `path`, `status` (`2xx`/`3xx`/`4xx`/`5xx`) |
| `http_request_duration_seconds` | histogram | `method`, `path` |
| `http_requests_inflight` | gauge | `method`, `path` |
| `seedbank_dwh_dispatch_total` | counter | `task`, `result` (`ok`/`disabled`/`error`) |
| `seedbank_dwh_task_duration_seconds` | histogram | `task`, `result` |
| `seedbank_inference_total` | counter | `kind`, `backend`, `status` |
| `seedbank_inference_duration_seconds` | histogram | `kind`, `backend` |
| `seedbank_experiment_run_total` | counter | `status` |
| `seedbank_auth_login_total` | counter | `result` |

The `path` label is always the **route template**
(`/api/v1/users/{id}`) — never the raw URL — so per-UUID requests do not
explode cardinality.

Set `ENABLE_METRICS=false` to disable the middleware and the endpoint
entirely. Default is on.

### Prometheus + Grafana stack (opt-in)

```bash
make up-obs
# or, equivalently:
docker compose --profile obs up -d prometheus grafana
```

Adds two containers:

| Service | Image | Port | Purpose |
|---|---|---|---|
| `prometheus` | `prom/prometheus:v2.55.1` | `127.0.0.1:9090` | Scrapes `api:8000/metrics` every 15 s, 7-day retention |
| `grafana` | `grafana/grafana:11.3.0` | `127.0.0.1:3000` | Auto-loads the Prometheus datasource and the **Seed-Bank — Overview** dashboard |

`GRAFANA_PASSWORD` is **required** (no default — the container fails
to start if unset, by design). `GRAFANA_USER` defaults to `admin`. Set
both in `.env` before `make up-obs`. Sign-up and anonymous access are
off by default; cookies are SameSite=strict, gravatar is disabled, and
`X-Content-Type-Options` / `X-XSS-Protection` headers are forced on.

Both services live behind the `obs` Compose profile so the default
`make up` stack stays at the same resource budget. Configuration is
checked into the repo at `ops/prometheus/` and `ops/grafana/` —
mounted read-only so a container restart cannot drift the dashboard.

### Tracing — OpenTelemetry

Set `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317` (or your
Tempo / Jaeger endpoint) and the API + workers emit gRPC OTLP spans
covering FastAPI, SQLAlchemy, asyncpg, Redis, outbound httpx, and
Celery. Unset → all instrumentors are no-ops.

### Errors — Sentry

Set `SENTRY_DSN` to forward unhandled exceptions; the SDK lights up the
FastAPI, Starlette, and Celery integrations automatically. Defaults to
10% trace sampling (`SENTRY_TRACES_SAMPLE_RATE=0.1`); profiling is off
(`SENTRY_PROFILES_SAMPLE_RATE=0.0`). PII is never sent
(`send_default_pii=false`).

## Production overlay (TBD)

`compose.prod.yaml` will be added in Phase 10 with: resource limits
tightened, secrets via Compose `secrets:` instead of env, restart
policies, log driver pinned to `json-file` with rotation, and the GPU
worker enabled by default.
