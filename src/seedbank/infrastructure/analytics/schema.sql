-- ClickHouse schema for the seed-bank data warehouse.
--
-- This file is the source of truth for the OLAP star schema. It's applied
-- by ``seedbank.infrastructure.analytics.migrate.apply_schema`` at boot
-- (via ``scripts/init_clickhouse.py``). Every statement is
-- ``CREATE TABLE IF NOT EXISTS`` so the runner is idempotent — production
-- can rerun it on every deploy without breaking.
--
-- Engine choice: ``ReplacingMergeTree`` for both dims and facts so the
-- Celery dual-write path can deliver "at-least-once" without producing
-- duplicate rows at query time (the engine de-dups on its sort key,
-- keeping the row with the highest ``_ingested_at``).
--
-- Time columns are ``DateTime64(3, 'UTC')`` end-to-end; queries should
-- always pass UTC. ``occurred_date`` materialised columns power partition
-- pruning and "by day" rollups without needing a separate calendar table.
--
-- Schema evolution note: ``IF NOT EXISTS`` only protects creation; column
-- type changes are NOT picked up automatically. To re-apply nullable-column
-- corrections on a live cluster:
--   ALTER TABLE fact_detection MODIFY COLUMN quality LowCardinality(Nullable(String));
--   ALTER TABLE fact_experiment_result MODIFY COLUMN user_id Nullable(UUID);
-- On dev clusters with no meaningful data, the simplest path is
-- ``DROP TABLE`` + re-run ``scripts/init_clickhouse.py``.

-- ── Dimensions ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS dim_user (
    user_id     UUID,
    email       String,
    role        LowCardinality(String),
    is_active   UInt8,
    is_verified UInt8,
    created_at  DateTime64(3, 'UTC'),
    updated_at  DateTime64(3, 'UTC')
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (user_id);

CREATE TABLE IF NOT EXISTS dim_seed_type (
    seed_type_id                 UUID,
    code                         String,
    display_name                 String,
    default_confidence_threshold Decimal(5, 4),
    created_at                   DateTime64(3, 'UTC'),
    updated_at                   DateTime64(3, 'UTC')
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (seed_type_id);

CREATE TABLE IF NOT EXISTS dim_model (
    model_id     UUID,
    name         String,
    version      String,
    kind         LowCardinality(String),
    backend      LowCardinality(String),
    seed_type_id Nullable(UUID),
    status       LowCardinality(String),
    created_at   DateTime64(3, 'UTC'),
    updated_at   DateTime64(3, 'UTC')
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY (model_id);

-- ── Facts ───────────────────────────────────────────────────────────────

-- One row per ``inferences`` row. Powers per-model latency / throughput /
-- error-rate dashboards and the ``/api/v1/models/{id}/performance`` endpoint.
CREATE TABLE IF NOT EXISTS fact_inference (
    inference_id   UUID,
    image_id       UUID,
    batch_id       UUID,
    user_id        UUID,
    model_id       UUID,
    seed_type_id   Nullable(UUID),
    backend        LowCardinality(String),
    model_kind     LowCardinality(String),
    latency_ms     Nullable(UInt32),
    has_error      UInt8,
    occurred_at    DateTime64(3, 'UTC'),
    occurred_date  Date MATERIALIZED toDate(occurred_at),
    _ingested_at   DateTime64(3, 'UTC') DEFAULT now64(3, 'UTC')
)
ENGINE = ReplacingMergeTree(_ingested_at)
PARTITION BY toYYYYMM(occurred_at)
ORDER BY (model_id, occurred_at, inference_id);

-- One row per ``seed_detections`` row. Powers quality distributions,
-- per-class confidence histograms.
CREATE TABLE IF NOT EXISTS fact_detection (
    detection_id          UUID,
    inference_id          UUID,
    image_id              UUID,
    batch_id              UUID,
    user_id               UUID,
    model_id              UUID,
    seed_type_id          Nullable(UUID),
    quality               LowCardinality(Nullable(String)),
    confidence            Decimal(5, 4),
    detection_confidence  Decimal(5, 4),
    box_x_norm            Decimal(7, 6),
    box_y_norm            Decimal(7, 6),
    box_w_norm            Decimal(7, 6),
    box_h_norm            Decimal(7, 6),
    width_px              Nullable(UInt32),
    height_px             Nullable(UInt32),
    area_px               Nullable(UInt64),
    aspect_ratio          Nullable(Decimal(7, 4)),
    occurred_at           DateTime64(3, 'UTC'),
    occurred_date         Date MATERIALIZED toDate(occurred_at),
    _ingested_at          DateTime64(3, 'UTC') DEFAULT now64(3, 'UTC')
)
ENGINE = ReplacingMergeTree(_ingested_at)
PARTITION BY toYYYYMM(occurred_at)
ORDER BY (model_id, occurred_at, detection_id);

-- One row per ``experiment_results`` row. Enables ad-hoc model comparison
-- queries beyond the snapshot in ``model_metrics``.
CREATE TABLE IF NOT EXISTS fact_experiment_result (
    result_id        UUID,
    experiment_id    UUID,
    dataset_id       UUID,
    dataset_item_id  UUID,
    model_id         UUID,
    user_id          Nullable(UUID),
    has_error        UInt8,
    latency_ms       Nullable(UInt32),
    occurred_at      DateTime64(3, 'UTC'),
    occurred_date    Date MATERIALIZED toDate(occurred_at),
    _ingested_at     DateTime64(3, 'UTC') DEFAULT now64(3, 'UTC')
)
ENGINE = ReplacingMergeTree(_ingested_at)
PARTITION BY toYYYYMM(occurred_at)
ORDER BY (model_id, occurred_at, result_id);

-- One row per ``scan_batches`` row, refreshed on every status transition.
-- ReplacingMergeTree dedupes by ``batch_id`` on merge, so the latest
-- snapshot wins. Useful for queue-health dashboards.
CREATE TABLE IF NOT EXISTS fact_scan_batch (
    batch_id         UUID,
    user_id          UUID,
    supplier_id      Nullable(UUID),
    status           LowCardinality(String),
    source           LowCardinality(String),
    image_count      UInt32,
    duration_ms      Nullable(UInt32),
    submitted_at     DateTime64(3, 'UTC'),
    started_at       Nullable(DateTime64(3, 'UTC')),
    finished_at      Nullable(DateTime64(3, 'UTC')),
    geo_country_code LowCardinality(String),
    submitted_date   Date MATERIALIZED toDate(submitted_at),
    _ingested_at     DateTime64(3, 'UTC') DEFAULT now64(3, 'UTC')
)
ENGINE = ReplacingMergeTree(_ingested_at)
PARTITION BY toYYYYMM(submitted_at)
ORDER BY (user_id, submitted_at, batch_id);
