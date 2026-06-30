# 02 — Containers (Compose stack)

The runtime topology one level deeper than [system context](01-system-context.md):
each box is a process declared in `compose.yaml`. Healthchecks and
dependencies match the file exactly.

## Diagram

```mermaid
flowchart TB
    Client[[HTTP client<br/>browser / curl / SDK]]

    subgraph App["Application layer"]
        API["api<br/>seedbank/api:0.1.0<br/>uvicorn :8000<br/>1.5 cpu / 768M"]
        WCPU["worker-cpu<br/>celery -Q default,cdc,housekeeping,experiments,dwh<br/>1 cpu / 512M"]
        WINF["worker-inference<br/>(target: runtime-inference-cpu-full)<br/>celery -Q inference,evaluation<br/>2 cpu / 4G — prod overlay swaps to runtime-gpu"]
    end

    subgraph Data["Stateful services"]
        PG[(postgres:16<br/>:5432<br/>logical replication on)]
        RD[(redis:7<br/>:6379<br/>db0=cache, db1=broker, db2=results)]
        MIN[(minio<br/>:9000 api / :9001 console<br/>buckets: seedbank-images, seedbank-models, seedbank-experiments, seedbank-datasets)]
        CH[(clickhouse:24.10<br/>:8123<br/>OLAP / metrics)]
    end

    subgraph Tooling["ML / ops tooling"]
        ADM["adminer<br/>(profile: dev)"]
        CHUI["ch-ui<br/>(profile: dev)"]
        PROM["prometheus<br/>(profile: obs)"]
        GRAF["grafana<br/>(profile: obs)"]
        FE["frontend / nginx<br/>(profile: frontend)"]
    end

    Client -->|":8000"| API

    API --> PG
    API --> RD
    API --> MIN
    API --> CH
    API -. "send_task" .-> RD

    WCPU --> PG
    WCPU --> RD
    WCPU --> MIN

    WINF --> PG
    WINF --> RD
    WINF --> MIN

    ADM -.-> PG
    CHUI -.-> CH
    PROM -.-> API
    GRAF -.-> PROM
    FE -.-> API
```

## What runs where

| Service | Image | Purpose | Healthcheck |
|---|---|---|---|
| `api` | `seedbank/api:0.1.0` (target `runtime-cpu`) | FastAPI HTTP surface, all routers under `/api/v1` | `GET /readyz` |
| `worker-cpu` | `seedbank/worker-cpu:0.1.0` | Celery worker for default/cdc/housekeeping/experiments/dwh queues. CPU-only bookkeeping, experiments, and DWH dual-write. | `celery inspect ping` |
| `worker-inference` | `seedbank/worker-inference:0.1.0` (target `runtime-inference-cpu-full` in dev, `runtime-gpu` via the prod overlay) | Celery worker for inference + evaluation queues. Always-on in the default profile; runs CPU torch by default, GPU only under `compose.prod.yaml`. | none in compose |
| `postgres` | `postgres:16-alpine` | OLTP. `wal_level=logical` is on for the future ClickHouse CDC pipeline. | `pg_isready` |
| `redis` | `redis:7-alpine` | Three logical DBs: 0 (cache), 1 (Celery broker), 2 (Celery result backend). 256M LRU cap. | `redis-cli ping` |
| `minio` | `minio:RELEASE.2024-11-07` | Object store. Buckets are seeded by `make seed`. | `/minio/health/live` |
| `clickhouse` | `clickhouse-server:24.10-alpine` | OLAP analytics store. Populated by the app-level DWH dual-write; powers the analytics dashboard (windowed trends). | `/ping` |
| `adminer` | `adminer:4.8.1` | Postgres DB UI. **`dev` profile only.** | none |
| `ch-ui` | `ghcr.io/caioricciuti/ch-ui` | ClickHouse DB UI (`:3488`). **`dev` profile only.** | none |
| `prometheus` | `prom/prometheus` | Scrapes `api:8000/metrics`, 7-day TSDB (`:9090`). **`obs` profile only.** | none |
| `grafana` | `grafana/grafana` | Auto-provisioned dashboards (`:3000`). **`obs` profile only.** | none |
| `frontend` | built React SPA on nginx | Serves the web client on `:5173`. **`frontend` profile only.** | none |

## Network and ports

- All services are on the user-defined `seedbank-net` bridge.
- Every host port is bound to `127.0.0.1` (no public exposure on the
  host) — production would put the API behind a real ingress and never
  expose Postgres/Redis/MinIO to the host network.

## Volumes

- `postgres-data` → `/var/lib/postgresql/data`
- `redis-data` → `/data` (AOF on)
- `minio-data` → `/data`
- `clickhouse-data` → `/var/lib/clickhouse`

The four named volumes are the only state. `make down -v` is
destructive; `make down` is safe.
