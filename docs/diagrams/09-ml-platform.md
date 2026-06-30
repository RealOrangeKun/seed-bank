# 09 — ML Platform

How a trained `.pth` becomes production traffic, how the production
model is resolved for a segment, and how an AI developer overrides the
resolver for one request.

## Model lifecycle

```mermaid
stateDiagram-v2
    [*] --> registered : scripts/register_model.py<br/>(uploads weights to MinIO,<br/>POST /api/v1/models)

    registered --> staging : PATCH /api/v1/models/{id}<br/>{status: "staging"}
    staging --> production : PATCH /api/v1/models/{id}<br/>{status: "production"}<br/>(usually after experiment + canary)
    production --> archived : PATCH /api/v1/models/{id}<br/>{status: "archived"}<br/>(superseded by a newer version)

    staging --> archived : promotion abandoned
    registered --> archived : never used

    note right of registered
        artifact_uri points to
        s3://seedbank-models/...
        config holds builder key
        + class names + thresholds
    end note

    note right of production
        served by ModelResolver for its
        (kind, seed_type_id) segment.
        per-request model_id override
        also requires status ∈ {staging, production}
    end note
```

Status enum: `infrastructure/db/enums.py::ModelStatus`.

## Model resolution decision tree

`services/model_resolver.py::ModelResolver.resolve_model`. Called by
both the worker (one detect call + one classify call per image) and
the experiment runner. There is no A/B / weighted-split routing: the
resolver returns the **`production`** model for the segment, with a
global (seed-type-agnostic) production fallback.

```mermaid
flowchart TD
    REQ["resolve_model(kind, seed_type_id)"]

    OVR{"per-request<br/>model_id<br/>override?"}
    OVRSCOPE{"caller in<br/>{ai_developer, admin}?<br/>+ artifact.status ∈<br/>{staging, production}?"}
    OVR_OK[return overridden model]
    OVR_DENY[ForbiddenError /<br/>ModelNotReadyError]

    SEG{"production model for<br/>(kind, seed_type_id)?"}
    SEGOK[return that model]
    GLOBAL{"global production model<br/>for kind<br/>(seed_type_id = NULL)?"}
    GLOBALOK[return global model]
    EMPTY[ModelNotReadyError]

    REQ --> OVR
    OVR -- yes --> OVRSCOPE
    OVRSCOPE -- yes --> OVR_OK
    OVRSCOPE -- no --> OVR_DENY
    OVR -- no --> SEG
    SEG -- yes --> SEGOK
    SEG -- no --> GLOBAL
    GLOBAL -- yes --> GLOBALOK
    GLOBAL -- no --> EMPTY
```

## Per-request override (the AI-developer escape hatch)

The platform's "let me try this model on this exact image without
touching the production model" path. Allowed for `ai_developer` and
`admin` only.

```mermaid
sequenceDiagram
    autonumber
    actor AID as AI developer
    participant API as POST /analyze
    participant AS as AnalysisService
    participant W as worker.analyze_image
    participant TR as ModelResolver

    AID->>API: POST /analyze<br/>files=…<br/>model_id=<UUID>
    API->>AS: create_and_dispatch(actor, files, model_id_override=UUID)
    alt actor.role == end_user
        AS-->>API: ForbiddenError
        API-->>AID: 403 Problem Details
    else ai_developer / admin
        AS->>AS: persist batch + dispatch tasks (override piggybacks)
        AS-->>API: 202
        API-->>AID: 202 Accepted
    end

    note over W: per-image task picks override
    W->>TR: resolve override<br/>(verify status ∈ {staging, production})
    TR-->>W: ModelArtifact OR ModelNotReadyError
    W->>W: detect/classify with overridden model
    W->>W: persist inferences.model_id = override<br/>(traceable per pillar 5)
```

## Backends: pluggable inference

`infrastructure/ml/backends/`:

| Backend | When | Notes |
|---|---|---|
| `torch_local` | First-party `.pth` weights loaded from MinIO + a registered `@register_builder("…")` arch | Default. Cached in `ModelManager`. |
| `roboflow` | `model.backend = "roboflow"`; calls Roboflow Inference API over `httpx.AsyncClient` | No GPU needed locally. Rate-limited by RB's plan. |
| `yolo` | `model.backend = "yolo"`; uses `ultralytics` package | For YOLOv8/v11 family. |

A new model architecture = one file under `builders/<key>.py` with
`@register_builder("<key>")`. No backend changes. No router changes.

## Pipeline construction

```mermaid
flowchart TB
    REQ["pipeline_factory.get_detect_pipeline(model_artifact)"]
    MM[ModelManager.load<br/>per-process LRU cache,<br/>keyed by model_id]
    BLD[builders/&lt;key&gt;.py<br/>@register_builder]
    BCK[backends/<br/>torch_local / roboflow / yolo]
    PIPE[DetectPipeline /<br/>ClassifyPipeline]

    REQ --> MM
    MM --> BLD
    MM --> BCK
    BLD --> PIPE
    BCK --> PIPE
```

Builders construct the bare arch + load weights from MinIO. Backends
own the "actually run inference" call. Pipeline glues pre-processing
(PIL → tensor) and post-processing (logits → bbox/quality) and is
what the worker actually invokes.
