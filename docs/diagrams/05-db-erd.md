# 05 — Database ERD

The Postgres schema as defined in
`src/seedbank/infrastructure/db/models.py`. Every PK is `uuid7()` from
`core/ids.py`. Soft delete is reserved for user-visible aggregates
(`scan_batches`, `datasets`, `users`); internal tables use hard delete
with `ON DELETE CASCADE`.

## Diagram

```mermaid
erDiagram
    USERS ||--o{ OAUTH_ACCOUNTS : "has"
    USERS ||--o{ REFRESH_TOKENS : "issues"
    USERS ||--o{ API_KEYS : "owns"
    USERS ||--o{ AUDIT_LOG : "actor"
    USERS ||--o{ SCAN_BATCHES : "submits"
    USERS ||--o{ SUPPLIERS : "creates"
    USERS ||--o{ MODEL_ARTIFACTS : "registers"
    USERS ||--o{ DATASETS : "creates"
    USERS ||--o{ EXPERIMENTS : "runs"

    SEED_TYPES ||--o{ MODEL_ARTIFACTS : "scopes"
    SEED_TYPES ||--o{ SEED_DETECTIONS : "labels"

    SUPPLIERS ||--o{ SCAN_BATCHES : "branded"

    MODEL_ARTIFACTS ||--o{ MODEL_METRICS : "scored by"
    MODEL_ARTIFACTS ||--o{ EXPERIMENTS : "evaluated"
    MODEL_ARTIFACTS ||--o{ INFERENCES : "produced"

    DATASETS ||--o{ DATASET_ITEMS : "contains"
    DATASETS ||--o{ MODEL_METRICS : "evaluated against"
    DATASETS ||--o{ EXPERIMENTS : "uses"

    EXPERIMENTS ||--o{ EXPERIMENT_RESULTS : "yields"
    DATASET_ITEMS ||--o{ EXPERIMENT_RESULTS : "scored"

    SCAN_BATCHES ||--o{ SCAN_IMAGES : "groups"
    SCAN_IMAGES ||--o{ INFERENCES : "scored by"
    INFERENCES ||--o{ SEED_DETECTIONS : "produces"

    USERS {
        uuid id PK
        citext email UK
        string hashed_password
        string role "admin/ai_developer/end_user"
        bool is_active
        bool is_verified
        timestamptz last_login_at
    }

    OAUTH_ACCOUNTS {
        uuid id PK
        uuid user_id FK
        string provider "google/github"
        string provider_subject
        text access_token_encrypted
    }

    REFRESH_TOKENS {
        uuid id PK
        uuid user_id FK
        string token_hash
        timestamptz expires_at
        timestamptz revoked_at
        uuid replaced_by_id FK "rotation chain"
        inet ip
    }

    API_KEYS {
        uuid id PK
        uuid user_id FK
        string key_hash UK
        string prefix
        text_array scopes
        timestamptz expires_at
        timestamptz revoked_at
    }

    AUDIT_LOG {
        uuid id PK
        uuid actor_id FK
        string action
        string target_type
        string target_id
        jsonb audit_metadata
        inet ip
        timestamptz occurred_at
    }

    SEED_TYPES {
        uuid id PK
        string code UK
        string display_name
        numeric default_confidence_threshold
    }

    SUPPLIERS {
        uuid id PK
        citext name
        string slug UK
        bool is_global
        uuid created_by_user_id FK
    }

    MODEL_ARTIFACTS {
        uuid id PK
        string name
        string version
        string kind "detection/classification"
        string backend "torch_local/roboflow/yolo"
        uuid seed_type_id FK
        string artifact_uri "minio://"
        jsonb config
        string status "registered/staging/production/archived"
    }

    MODEL_METRICS {
        uuid id PK
        uuid model_id FK
        uuid dataset_id FK
        string metric_name
        numeric metric_value
        timestamptz computed_at
    }

    DATASETS {
        uuid id PK
        string name UK
        uuid created_by FK
    }

    DATASET_ITEMS {
        uuid id PK
        uuid dataset_id FK
        string image_storage_key
        jsonb ground_truth
    }

    EXPERIMENTS {
        uuid id PK
        string name
        string status "pending/running/succeeded/failed"
        uuid model_id FK
        uuid dataset_id FK
        bigint duration_ms
        jsonb summary_metrics
    }

    EXPERIMENT_RESULTS {
        uuid id PK
        uuid experiment_id FK
        uuid dataset_item_id FK
        jsonb predicted_boxes
        int latency_ms
        text error
    }

    SCAN_BATCHES {
        uuid id PK
        uuid user_id FK
        uuid supplier_id FK
        string status "pending/running/succeeded/failed/partial"
        string source "api/web/sdk/mobile/mobile_realtime"
        timestamptz submitted_at
        timestamptz started_at
        timestamptz finished_at
        bigint duration_ms
        numeric gps_lat
        numeric gps_long
        string geo_country_code
    }

    SCAN_IMAGES {
        uuid id PK
        uuid batch_id FK
        string storage_key "minio key"
        string content_type
        bigint size_bytes
        string sha256
        int width
        int height
        timestamptz uploaded_at
    }

    INFERENCES {
        uuid id PK
        uuid image_id FK
        uuid model_id FK "AUDIT ANCHOR"
        string backend
        int latency_ms
        text error
        timestamptz occurred_at
    }

    SEED_DETECTIONS {
        uuid id PK
        uuid inference_id FK
        uuid seed_type_id FK
        string quality "good/bad"
        numeric confidence "5,4"
        numeric detection_confidence "5,4"
        numeric box_x_norm "7,6"
        numeric box_y_norm "7,6"
        numeric box_w_norm "7,6"
        numeric box_h_norm "7,6"
        int area_px
        numeric aspect_ratio
    }
```

## Key invariants

- **Pillar 5 — traceability:** every `seed_detections` row points to
  one `inferences` row, which points to exactly one `model_artifacts`
  row. You can always answer "which model produced this result"
  without joining through audit logs.
- **`uq_inferences_image_model`** — one inference row per `(image_id,
  model_id)`. A re-run with the same model is an update, not a
  duplicate row.
- **`uq_scan_images_batch_storage_key`** — dedup inside a batch via
  the storage key (which embeds the sha256). Re-uploading the same
  bytes in the same batch fails fast.
- **Bounding boxes are normalized 0–1** (`NUMERIC(7,6)`). Pixel
  coordinates are derived at render time, not stored.
- **Confidences are `NUMERIC(5,4)`** — money-style precision. Floats
  would lose the last digit in arithmetic and break the audit trail.
- **`audit_log`** is append-only and indexed by `(actor_id,
  occurred_at)`. Soft deletes don't apply.
