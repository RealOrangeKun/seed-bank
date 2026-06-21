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
        WCPU["worker-cpu<br/>celery -Q default,cdc,housekeeping<br/>1 cpu / 512M"]
        WGPU["worker-inference<br/>(profile: gpu)<br/>celery -Q inference,evaluation<br/>1 nvidia gpu / 8G"]
    end

    subgraph Data["Stateful services"]
        PG[(postgres:16<br/>:5432<br/>logical replication on)]
        RD[(redis:7<br/>:6379<br/>db0=cache, db1=broker, db2=results)]
        MIN[(minio<br/>:9000 api / :9001 console<br/>buckets: seed-bank, seedbank-models, seedbank-experiments)]
        CH[(clickhouse:24.10<br/>:8123<br/>OLAP / metrics)]
    end

    subgraph Tooling["ML / ops tooling"]
        ML[mlflow:v2.18<br/>:5000<br/>backend=postgres, artifacts=minio]
        ADM["adminer<br/>(profile: dev)"]
    end

    Client -->|":8000"| API

    API --> PG
    API --> RD
    API --> MIN
    API --> CH
    API -. "send_task" .-> RD
    API --> ML

    WCPU --> PG
    WCPU --> RD
    WCPU --> MIN

    WGPU --> PG
    WGPU --> RD
    WGPU --> MIN

    ML --> PG
    ML --> MIN

    ADM -.-> PG
```

## What runs where

| Service | Image | Purpose | Healthcheck |
|---|---|---|---|
| `api` | `seedbank/api:0.1.0` (target `runtime-cpu`) | FastAPI HTTP surface, all routers under `/api/v1` | `GET /readyz` |
| `worker-cpu` | `seedbank/worker-cpu:0.1.0` | Celery worker for default/cdc/housekeeping queues. CPU-only model paths and bookkeeping tasks. | `celery inspect ping` |
| `worker-inference` | `seedbank/worker-inference:0.1.0` (target `runtime-gpu`) | Celery worker for inference + evaluation queues. **`gpu` profile only** — laptops without CUDA bring up everything else. | none in compose |
| `postgres` | `postgres:16-alpine` | OLTP. `wal_level=logical` is on for the future ClickHouse CDC pipeline. | `pg_isready` |
| `redis` | `redis:7-alpine` | Three logical DBs: 0 (cache), 1 (Celery broker), 2 (Celery result backend). 256M LRU cap. | `redis-cli ping` |
| `minio` | `minio:RELEASE.2024-11-07` | Object store. Buckets are seeded by `make seed`. | `/minio/health/live` |
| `clickhouse` | `clickhouse-server:24.10-alpine` | OLAP. Today: served by `GET /api/v1/models/{id}/performance`. Tomorrow: experiment fact rows + per-detection telemetry. | `/ping` |
| `mlflow` | `ghcr.io/mlflow/mlflow:v2.18.0` | Tracking server. Backend = postgres `mlflow` DB; artifacts = MinIO `seedbank-experiments`. | `/health` |
| `adminer` | `adminer:4.8.1` | DB UI for dev. **`dev` profile only.** | none |

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
