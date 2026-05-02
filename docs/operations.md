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
| `worker-cpu` | same image as `api` | Celery worker for `default,cdc,housekeeping,experiments,dwh` queues (no torch) |
| `worker-inference` | `seedbank/worker-inference:0.1.0` | Celery worker for `inference,evaluation`. Dev: CPU torch wheels (`runtime-inference-cpu` target). Prod overlay: CUDA (`runtime-gpu`). |
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
- **Inference batch stuck in `pending`**: the worker that serves the
  `inference` queue is `worker-inference`, not `worker-cpu` (the CPU
  image has no torch by design). Make sure `worker-inference` is up:
  `docker compose ps worker-inference` should show `healthy`. `make up`
  brings it up by default; if you used `make up-no-inference` to skip
  the heavy build, switch to `make up`.
- **`Received unregistered task of type 'seedbank.analyze_image'`**:
  rebuild the worker image. The task modules are imported from
  `src/seedbank/workers/tasks/__init__.py`; if your local copy is
  pre-Phase-10 the file is empty and Celery never picks them up.

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
| `http_requests_inflight` | gauge | `method` |
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

## Production overlay

Prod runs as a single overlay on top of the dev compose:

```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d
# or:
make up-prod
```

`compose.prod.yaml` only sets the deltas — service definitions,
images, healthcheck logic, and named volumes still come from
`compose.yaml`. The deltas are: file-based secrets, hardening,
resource caps, restart policy, log rotation, dropped external ports,
and GPU worker default-on.

### First-time secret setup

Secrets live in `./secrets/`. Expected files (all `chmod 0400`,
created with `printf '%s' ...` so there's no trailing newline):

| File | Used by |
|---|---|
| `postgres_password` | postgres (`POSTGRES_PASSWORD_FILE`); api, workers, mlflow read it via an entrypoint shim |
| `jwt_secret` | api, workers (Pydantic `secrets_dir`) |
| `minio_access_key` / `minio_secret_key` | api, workers (Pydantic); minio + mlflow via entrypoint shim |
| `clickhouse_password` | api, workers (Pydantic); clickhouse via entrypoint shim |
| `roboflow_api_key` | api, workers (Pydantic, optional) |
| `sentry_dsn` | api, workers (Pydantic, optional — empty file = Sentry off) |
| `grafana_admin_password` | grafana (`GF_SECURITY_ADMIN_PASSWORD__FILE`) |

The exact recipe is in `secrets/README.md`. The directory itself is
checked in (with a `.gitignore` blocking everything but the README +
gitignore), so a fresh clone has the right shape.

`make secrets-check` walks `./secrets/` and fails if any expected file
is missing or has perms other than `0400`. Run it before `make
up-prod` (the target depends on it).

Ownership: secrets are mounted into containers as root-owned 0400
files at `/run/secrets/<name>`. No container user except root can
read them by default. The api / worker entrypoint shim runs **before**
`tini`/`USER seedbank` only inasmuch as Compose mounts the file before
process start; the shim itself runs as `seedbank` (uid 10001) and
reads the file via `cat`. That works because Compose mounts secrets
world-readable inside the namespace by default — verify with
`docker exec <ctn> ls -l /run/secrets/`. If a future hardening pass
needs root-only secrets, add `uid: 10001, mode: 0400` to each secret
mount.

### `make up-prod` flow

1. `secrets-check` runs first. Failure here aborts the bring-up.
2. Compose merges `compose.yaml` + `compose.prod.yaml` and starts the
   stack detached. No image build — prod assumes pre-built tags
   (`seedbank/api:0.1.0`, `seedbank/worker-cpu:0.1.0`,
   `seedbank/worker-inference:0.1.0`). Building in prod is a separate
   CI step.
3. Healthchecks at 30 s intervals; the api stays at 10 s because
   `/readyz` is what the load balancer scrapes.

### Resource caps — how they were chosen

Single-box prod target: a 16 GB / 8 vCPU host. The caps below sum to
roughly 12 GB / 13 vCPU (over-subscribed on CPU, deliberately — only
the inference worker actually pegs CPU during a batch).

| Service | CPUs | Memory | Rationale |
|---|---|---|---|
| api | 2.0 | 1.5G | ~50 rps headroom; tighter than dev because workers contend for CPU |
| worker-cpu | 2.0 | 1G | Bursty CDC + housekeeping; modest memory |
| worker-inference | (uncapped CPU) | 8G | torch + CUDA contexts + image batches |
| postgres | 2.0 | 2G | Lets `shared_buffers` grow without page-cache thrash |
| clickhouse | 2.0 | 4G | Columnar engine wants page-cache headroom |
| redis | 1.0 | 512M | Small dataset, LRU eviction |
| minio | 1.0 | 1G | Mostly proxying to disk |
| mlflow | 0.5 | 512M | UI + REST, rare load |
| prometheus | 1.0 | 1G | 7-day TSDB on a single api scrape target |
| grafana | 0.5 | 512M | Single-user admin |

### Dropped ports

Only **api:8000** and **grafana:3000** are bound externally. Postgres,
Redis, MinIO (both 9000 + 9001), ClickHouse, MLflow, and Prometheus
stay on the internal `seedbank-net` bridge — reach them with
`docker compose exec` or via Grafana's pre-provisioned datasource.

### GPU verification

```bash
docker compose -f compose.yaml -f compose.prod.yaml exec worker-inference nvidia-smi
```

Expect a populated table. If you see "command not found" or "no
devices", the host's `nvidia-container-toolkit` isn't installed or
the daemon hasn't been restarted since installing it.

A CPU-only prod fallback is supported but not the default. The dev
compose builds `worker-inference` from the `runtime-inference-cpu`
Dockerfile target (torch CPU wheels, ~1.5 GB image, no GPU
required). The prod overlay swaps it to `runtime-gpu` and re-adds the
GPU device reservation. To run prod on a CPU-only host, drop the
`build.target` and the `deploy.resources.reservations.devices` block
from `worker-inference` in `compose.prod.yaml`.

### Secret rotation

Honest take: there is no live reload. `Settings` is constructed once
per process. Rotation requires a container restart.

```bash
# 1. Update the secret file.
printf '%s' "$(openssl rand -hex 32)" > secrets/jwt_secret
chmod 0400 secrets/jwt_secret

# 2. Restart the consumers.
docker compose -f compose.yaml -f compose.prod.yaml restart api worker-cpu worker-inference
```

Postgres password rotation is a two-step: `ALTER USER seedbank WITH
PASSWORD '...'` first, then update `secrets/postgres_password` and
restart everything that talks to Postgres (api, workers, mlflow).
Skip step 1 and you'll lock yourself out.

A real secret-rotation tool (Vault, sealed-secrets, etc.) is post-Phase-10.

### Log rotation

`json-file` driver, `max-size: 10m`, `max-file: 5` → ~50 MB cap per
service. Off-box log shipping (Loki, ELK, CloudWatch) is post-Phase-10.
For now `docker compose logs -f` is the access path; for a static
snapshot pipe through `jq`:

```bash
docker compose -f compose.yaml -f compose.prod.yaml logs api | jq -R 'fromjson?'
```
