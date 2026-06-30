# 10 — Deployment

The Compose deployment view with explicit profiles, ports, and the
build-target boundary between the CPU and GPU images. Maps directly
to `compose.yaml` + `Dockerfile` (multi-stage).

## Diagram

```mermaid
flowchart TB
    subgraph Host["Developer host (laptop or build server)"]
        direction TB

        subgraph Net["bridge network: seedbank-net"]
            direction TB

            subgraph App["Default profile (make up)"]
                API[api<br/>image: seedbank/api:0.1.0<br/>target: runtime-cpu<br/>port: 127.0.0.1:8000]
                WCPU[worker-cpu<br/>image: seedbank/worker-cpu:0.1.0<br/>target: runtime-cpu<br/>queues: default,cdc,housekeeping,experiments,dwh]
                WINF[worker-inference<br/>image: seedbank/worker-inference:0.1.0<br/>target: runtime-inference-cpu-full dev / runtime-gpu prod<br/>queues: inference,evaluation]
            end

            subgraph Data["Stateful — always on"]
                PG[(postgres:16-alpine<br/>:5432<br/>vol: postgres-data)]
                RD[(redis:7-alpine<br/>:6379<br/>vol: redis-data)]
                MIN[(minio<br/>:9000 / :9001<br/>vol: minio-data)]
                CH[(clickhouse:24.10-alpine<br/>:8123<br/>vol: clickhouse-data)]
            end

            subgraph Tooling["Opt-in profiles"]
                ADM["adminer:4.8.1 :8080<br/>ch-ui :3488<br/>profile: dev"]
                OBS["prometheus :9090<br/>grafana :3000<br/>profile: obs"]
                FE["frontend (nginx) :5173<br/>profile: frontend"]
            end
        end

        BUILD[/Dockerfile<br/>stages: builder → runtime-cpu<br/>runtime-inference-cpu / -cpu-full<br/>runtime-gpu/]
    end

    BUILD -. "build target" .-> API
    BUILD -. "build target" .-> WCPU
    BUILD -. "build target" .-> WINF

    API --> PG
    API --> RD
    API --> MIN
    API --> CH

    WCPU --> PG
    WCPU --> RD
    WCPU --> MIN

    WINF --> PG
    WINF --> RD
    WINF --> MIN

    ADM -.-> PG
    OBS -.-> API
    FE -.-> API
```

## Profiles

| Profile | Brings up | Why |
|---|---|---|
| (default) | api, worker-cpu, worker-inference, postgres, redis, minio, clickhouse | Full functional stack on a CPU-only laptop (worker-inference uses CPU torch wheels by default). |
| `dev` | + adminer + ch-ui | Local Postgres + ClickHouse DB browsers. Off in CI. |
| `obs` | + prometheus + grafana | Metrics scrape + dashboards. |
| `frontend` | + frontend (nginx) | Built React SPA on :5173. |

Activated via `make up` (default), `make up-dev`, `make up-obs`, or `make up-front`. GPU is enabled by the prod overlay (`compose.prod.yaml`), not a compose profile.

## Build stages (`Dockerfile`)

```mermaid
flowchart LR
    SRC[/repo source/]
    B[builder stages<br/>python:3.12-slim<br/>uv sync per runtime]
    CPU[runtime-cpu<br/>python:3.12-slim<br/>copies venv<br/>+ src/]
    INF[runtime-inference-cpu / -cpu-full<br/>python:3.12-slim<br/>+ CPU torch / +ultralytics<br/>+ src/]
    GPU[runtime-gpu<br/>nvidia/cuda:12.4-runtime<br/>+ GPU torch<br/>+ src/]

    SRC --> B
    B --> CPU
    B --> INF
    B --> GPU
```

`api` and `worker-cpu` share the **same** `runtime-cpu` image — the
only difference is the `command:` line in compose. `worker-inference`
is a separate image so the torch stack doesn't bloat the API
container: in dev it builds `runtime-inference-cpu-full` (CPU torch +
ultralytics), and the prod overlay swaps the target to `runtime-gpu`
(CUDA).

## Operational properties

- **Healthchecks** on every service that has a sensible probe; compose
  `depends_on: condition: service_healthy` enforces ordering at
  startup.
- **Resource limits** are set on every service via `deploy.resources`
  (a hint locally, enforced by Swarm/Kubernetes). The lean stack fits
  in ~3 GB RAM.
- **Restart policy** = `unless-stopped` on long-running services.
- **All host ports bind to `127.0.0.1`** — production deployment puts
  a real ingress in front and exposes only the API.
- **Secrets** flow as `${VAR}` references resolved from `.env`
  (gitignored). No secret literals in `compose.yaml`.
- **Logical replication** is enabled on Postgres
  (`wal_level=logical`, `max_replication_slots=4`) so the future CDC
  pipeline to ClickHouse can hook in without a restart.

## What's *not* in the dev compose

- **Sentry** — `SENTRY_DSN` is wired, no container.
- **Reverse proxy / TLS** — added at deployment time (Caddy or an
  ingress controller).
- **Object lifecycle policies on MinIO** — handled by `make seed`'s
  bucket setup script in dev; production sets retention on the
  bucket directly.
- **Backups** — Postgres + MinIO snapshots are an out-of-band concern
  in production; dev volumes are disposable.
