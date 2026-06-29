# 04 — Worker Components

Inside the `worker-cpu` / `worker-inference` container. The Celery
process subscribes to queues, picks up a task per image, and runs the
detect → classify → persist pipeline.

## Diagram

```mermaid
flowchart TB
    BRK[("Redis broker<br/>db1")]
    RES[("Redis result backend<br/>db2")]

    subgraph WK["worker-cpu / worker-inference"]
        direction TB

        APP["workers/celery_app.py<br/>app factory<br/>task_routes inference→inference queue<br/>acks_late, prefetch=1"]

        TASK["workers/tasks/analyze.py<br/>@celery_app.task seedbank.analyze_image<br/>sync entry → asyncio.run"]

        SS["workers/session.py<br/>worker_session_scope<br/>fresh AsyncEngine per task<br/>engine.dispose at exit"]

        subgraph IMPL["_async_analyze_image (the real work)"]
            direction TB
            CAS["CAS pending → running<br/>via ScanBatchRepository.cas_status"]
            FETCH["MinIO.get_object<br/>image bytes"]
            RES_DET["TrafficRouter.select_model<br/>kind=DETECTION<br/>or model_id_override + scope check"]
            DET["DetectPipeline.detect<br/>via ModelManager.load"]
            P_INF["InferenceRepository.add_inference<br/>+ SeedDetectionRepository.add_many"]
            COMMIT1["commit detect rows"]
            RES_CLS["TrafficRouter.select_model<br/>kind=CLASSIFICATION<br/>graceful skip if absent"]
            CROP["PIL crop per detection<br/>using normalized bbox × img.size"]
            CLS["ClassifyPipeline.classify"]
            P_QC["InferenceRepository.add_inference<br/>+ SeedDetectionRepository.update_quality_many"]
            COMMIT2["commit classify rows"]
            FIN["finalize batch:<br/>count distinct images with detect inference;<br/>CAS running → succeeded / partial / failed"]
        end

        REPOS["Repositories<br/>(reused from API)"]
        ORM[("AsyncSession<br/>per task")]
    end

    subgraph EXT["External adapters"]
        MIN[("MinIO")]
        ML["infrastructure/ml<br/>backends, manager, pipeline"]
        TR["services/traffic_router"]
    end

    BRK --> APP
    APP --> TASK
    TASK --> SS
    SS --> IMPL

    CAS --> FETCH --> RES_DET --> DET --> P_INF --> COMMIT1 --> RES_CLS --> CROP --> CLS --> P_QC --> COMMIT2 --> FIN

    RES_DET --> TR
    RES_CLS --> TR
    DET --> ML
    CLS --> ML
    FETCH --> MIN

    P_INF --> REPOS
    P_QC --> REPOS
    CAS --> REPOS
    FIN --> REPOS
    REPOS --> ORM

    TASK -. "result / state" .-> RES
```

## Why a fresh engine per task

Workers cannot reuse the API's process-wide `@lru_cache`'d
`AsyncEngine`. `asyncpg`'s connection pool binds to the event loop it
was created on, and each `asyncio.run(_async_analyze_image(...))`
creates a brand-new loop. Reusing the API's engine would crash with
"got Future <Future pending> attached to a different loop". The
`worker_session_scope()` helper builds and disposes a fresh
`create_async_engine` per task — the precedent is verbatim from
`scripts/register_model.py`.

## Task contract

| Field | Value |
|---|---|
| Name | `seedbank.analyze_image` |
| Args | `(image_id: str, model_id_override: str \| None, seed_type_id: str \| None)` |
| Queue | `inference` (routed via `task_routes`) |
| Retries | `max_retries=2`, `default_retry_delay=10s` |
| `autoretry_for` | `(ExternalServiceError,)` only — never retry on `ValidationError` / `NotFoundError` |
| Acknowledgement | `task_acks_late=True` (worker only acks after success or final failure) |
| Prefetch | `worker_prefetch_multiplier=1` (one inference at a time per worker) |

## Crash-safety invariants

1. The API commits the `scan_batch` + `scan_image` rows **before**
   dispatching to Celery. A worker never sees an orphan task.
2. Detect rows commit before classify runs. If classify fails, detect
   data isn't lost — the batch flips to `partial`, not `failed`.
3. Status flips are CAS (`UPDATE … WHERE status = expected RETURNING
   id`). Two workers racing on the same batch can't both flip it.
4. The PNG/JPEG bytes never live in the DB. Workers fetch from MinIO
   on demand and rely on `seed_detections.box_*_norm` (normalized
   0–1) so the source of truth survives image resizing.
