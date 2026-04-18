# Operations

How to run the stack locally, what each service does, what the
healthchecks mean, and how to debug a sick stack.

## TL;DR — running locally

First time on a fresh checkout:

```bash
make env            # creates .env from .env.example (idempotent)
make up-infra       # postgres + redis + minio + clickhouse only — no build, ~10s
make up             # full stack (builds api image first time, ~5–10 min)
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

## Production overlay (TBD)

`compose.prod.yaml` will be added in Phase 10 with: resource limits
tightened, secrets via Compose `secrets:` instead of env, restart
policies, log driver pinned to `json-file` with rotation, and the GPU
worker enabled by default.
