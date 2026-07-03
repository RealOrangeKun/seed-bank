"""Application settings.

The single source of truth for environment-driven configuration.
Anything that varies between dev / staging / prod lives here and only here.
Code that needs a setting receives it via the `Settings` object — never via
`os.environ`.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
        # File-based secrets in prod. Pydantic-Settings reads every file
        # under this directory whose name matches a field (lowercased)
        # and treats its contents as that field's value. The directory
        # is silently skipped when missing, so dev (no /run/secrets) is
        # unaffected. See `compose.prod.yaml` and `secrets/README.md`.
        secrets_dir="/run/secrets",
    )

    # ── Service identity ─────────────────────────────────────────────────────
    env: Literal["dev", "test", "staging", "prod"] = "dev"
    service_name: str = "seedbank-api"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    debug: bool = False

    # ── HTTP ─────────────────────────────────────────────────────────────────
    api_v1_prefix: str = "/api/v1"
    # ``NoDecode`` disables Pydantic-Settings' default JSON decoding for these
    # list fields so the env source hands us the raw string; the validator
    # below then splits on commas. Keeps ``CORS_ALLOW_ORIGINS=http://a,http://b``
    # ergonomic instead of forcing a JSON array.
    cors_allow_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    trusted_hosts: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["*"])

    @field_validator("cors_allow_origins", "trusted_hosts", mode="before")
    @classmethod
    def _parse_list(cls, v: object) -> object:
        """Accept a JSON array *or* a comma-separated string (a list passes
        through). ``NoDecode`` hands us the raw env string; we keep backward
        compatibility with the JSON-array form used in ``.env`` while also
        allowing the friendlier ``a,b,c``."""
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                return json.loads(s)
            return [item.strip() for item in s.split(",") if item.strip()]
        return v

    # ── Auth ─────────────────────────────────────────────────────────────────
    jwt_secret: SecretStr = SecretStr("change-me-in-prod")
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_seconds: int = 60 * 15  # 15 min
    jwt_refresh_ttl_seconds: int = 60 * 60 * 24 * 7  # 7 days
    bcrypt_rounds: int = 12

    # OAuth (filled in via env in prod)
    oauth_google_client_id: SecretStr | None = None
    oauth_google_client_secret: SecretStr | None = None
    oauth_redirect_base_url: str = "http://localhost:8000"
    # Where the OAuth callback bounces the browser after minting tokens — the
    # SPA route that reads them from the URL fragment and completes login.
    oauth_post_login_redirect_url: str = "http://localhost:5173/auth/callback"

    # ── Postgres ─────────────────────────────────────────────────────────────
    postgres_dsn: PostgresDsn = Field(  # type: ignore[assignment]
        default="postgresql+asyncpg://seedbank:seedbank@postgres:5432/seedbank"
    )
    postgres_pool_size: int = 10
    postgres_max_overflow: int = 5
    postgres_pool_timeout: int = 30
    postgres_echo: bool = False

    # ── Redis ────────────────────────────────────────────────────────────────
    redis_dsn: RedisDsn = Field(default="redis://redis:6379/0")  # type: ignore[assignment]

    # ── Celery ───────────────────────────────────────────────────────────────
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # ── MinIO ────────────────────────────────────────────────────────────────
    minio_endpoint: str = "minio:9000"
    minio_access_key: SecretStr = SecretStr("seedbank")
    minio_secret_key: SecretStr = SecretStr("seedbank-dev-secret")
    minio_secure: bool = False
    minio_bucket_images: str = "seedbank-images"
    minio_bucket_models: str = "seedbank-models"
    minio_bucket_experiments: str = "seedbank-experiments"
    minio_bucket_datasets: str = "seedbank-datasets"
    minio_presign_ttl_seconds: int = 60 * 5
    # ``minio_endpoint`` is the in-cluster host the API uses to read/write
    # objects. Presigned URLs, however, are handed to *browsers*, which cannot
    # resolve an internal compose hostname like ``minio:9000`` — and the URL
    # signature is bound to the host. ``minio_public_endpoint`` is therefore the
    # externally reachable host used *only* to sign GET URLs for clients.
    minio_public_endpoint: str = "localhost:9000"
    minio_public_secure: bool = False
    # SigV4 signing region. Supplying it explicitly lets the client sign
    # presigned URLs *offline* — otherwise miniopy-async issues a live
    # GetBucketLocation call to resolve the region, which the public presign
    # client cannot make (the browser-facing host is unreachable from the API).
    # MinIO's default region is ``us-east-1``.
    minio_region: str = "us-east-1"

    @field_validator("minio_public_endpoint")
    @classmethod
    def _validate_public_endpoint(cls, v: str) -> str:
        """Fail fast on a malformed public endpoint.

        This value signs URLs handed to browsers, so a wrong shape produces
        presigned links that 404 *at the client* — far from the misconfig and
        hard to trace. It must be a bare ``host`` or ``host:port`` (the scheme
        is decided by ``minio_public_secure``); a value carrying a scheme or a
        path is a configuration error, so reject it at startup rather than mint
        broken URLs in production.
        """
        s = v.strip()
        if not s:
            raise ValueError("minio_public_endpoint must not be empty")
        if "://" in s:
            raise ValueError(
                "minio_public_endpoint must be a bare host[:port] without a "
                f"scheme (set minio_public_secure instead); got {v!r}"
            )
        if "/" in s:
            raise ValueError(f"minio_public_endpoint must not contain a path; got {v!r}")
        return s

    # ── ClickHouse ───────────────────────────────────────────────────────────
    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = 8123
    clickhouse_user: str = "seedbank"
    clickhouse_password: SecretStr = SecretStr("seedbank-dev-secret")
    clickhouse_database: str = "seedbank"

    # ── Inference ────────────────────────────────────────────────────────────
    inference_default_backend: Literal["torch_local", "roboflow", "ultralytics_yolo"] = (
        "torch_local"
    )
    roboflow_api_key: SecretStr | None = None
    inference_max_image_bytes: int = 10 * 1024 * 1024
    inference_max_image_pixels: int = 4096 * 4096
    # Stage-2 (two-stage / "accurate") tuning. The torch classifier batches the
    # per-seed crops through one forward pass instead of one call per crop; this
    # caps the batch so a tray with hundreds of seeds doesn't blow up memory.
    inference_classify_batch_size: int = 32
    # U2NET (rembg) background removal before the specialist sees each crop.
    # Quality win on cluttered backgrounds but expensive per crop on CPU — the
    # dominant cost of "accurate" mode without a GPU. Set false to disable
    # globally regardless of a model's per-artifact ``segment`` config.
    inference_segmentation_enabled: bool = True
    # Per-image good/bad verdict: an image is a "good batch" when its share of
    # good seeds (good / (good + bad)) is >= this threshold; below it is a "bad
    # batch". Surfaced to clients on the batch-detail / shared responses so the
    # web verdict and the PDF report read from one configured value.
    good_batch_threshold: float = Field(default=0.65, ge=0.0, le=1.0)

    # ── Analyze endpoint ─────────────────────────────────────────────────────
    rate_limit_analyze_per_minute: int = 30
    analyze_max_files_per_request: int = 16
    analyze_max_image_bytes: int = 10 * 1024 * 1024
    analyze_allowed_mime_types: list[str] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/webp"]
    )
    # ── Video analyze (YOLO-only) ────────────────────────────────────────────
    # A video is analyzed by the inference worker: the YOLO one-shot detector
    # runs over its frames and the detection boxes are burned into a re-encoded
    # H.264 mp4 that the apps play back. The two-stage path is too slow per
    # frame, so video is YOLO-only.
    analyze_allowed_video_mime_types: list[str] = Field(
        default_factory=lambda: [
            "video/mp4",
            "video/quicktime",
            "video/webm",
            "video/x-msvideo",
            "video/x-matroska",
        ]
    )
    analyze_max_video_bytes: int = 200 * 1024 * 1024
    # Hard cap on frames YOLO actually runs on. A longer clip is strided
    # (``vid_stride``) so the annotated video still spans the whole video.
    analyze_video_max_frames: int = Field(default=300, ge=1, le=2000)
    # Cap on how many processed frames contribute detection rows for the
    # good/bad stats (the annotated video still shows every processed frame).
    analyze_video_max_stats_frames: int = Field(default=40, ge=1, le=500)
    # ── Dataset YOLO import ──────────────────────────────────────────────────
    # A labelled dataset is uploaded as one .zip (images/ + labels/, YOLO
    # `class_id xc yc w h`). The worker streams it to disk and unpacks one image
    # at a time, so this cap bounds decompressed size (a zip-bomb guard), not
    # worker RAM. Real datasets (hundreds of full-res JPEGs) run to ~1 GB.
    dataset_import_max_zip_bytes: int = 2 * 1024 * 1024 * 1024
    dataset_import_max_items: int = Field(default=5000, ge=1, le=20000)
    dataset_import_image_extensions: list[str] = Field(
        default_factory=lambda: [".jpg", ".jpeg", ".png", ".webp"]
    )
    # Test-only: when true, Celery tasks run inline in the calling process
    # (instead of being sent to a broker). Must remain False in prod.
    celery_task_always_eager: bool = False

    # ── Data warehouse ───────────────────────────────────────────────────────
    # Master switch for the OLTP→ClickHouse dual-write pipeline (Phase 8).
    # When false, the API + workers skip every DWH dispatch — useful for
    # local stacks without ClickHouse and for unit/e2e tests that don't
    # spin one up. Defaults to true so production gets warehouse data.
    dwh_enabled: bool = True

    # ── Observability ────────────────────────────────────────────────────────
    # OTel: when unset every instrumentor is a no-op and the app pays no
    # exporter cost. Set to ``http://otel-collector:4317`` (or your Tempo /
    # Jaeger / OTLP collector) to enable distributed tracing.
    otel_exporter_otlp_endpoint: str | None = None
    # Sentry: unset → no-op. ``traces_sample_rate`` is read by sentry_sdk;
    # ``profiles_sample_rate`` enables the Python profiler when > 0.
    sentry_dsn: SecretStr | None = None
    sentry_traces_sample_rate: float = 0.1
    sentry_profiles_sample_rate: float = 0.0
    # Prometheus ``/metrics`` endpoint and HTTP middleware kill switch.
    enable_metrics: bool = True

    # ── Rate limiting ────────────────────────────────────────────────────────
    rate_limit_per_minute: int = 120
    rate_limit_login_per_minute: int = 10
    rate_limit_register_per_minute: int = 5
    rate_limit_refresh_per_minute: int = 60
    # Storage backend for the slowapi limiter (the `limits` library). Defaults
    # to ``redis_dsn`` (see api/rate_limit.py); set to ``memory://`` in tests so
    # the import-time limiter never dials a real Redis.
    rate_limit_storage_uri: str | None = None

    # ── Email verification ───────────────────────────────────────────────────
    email_verification_ttl_seconds: int = 60 * 60 * 24  # 24h

    # ── First-admin bootstrap ────────────────────────────────────────────────
    # Shared-secret token required by ``POST /api/v1/auth/bootstrap-admin``.
    # The endpoint is idempotent (409 if any admin already exists), but the
    # token is the production tripwire — operators set it once at deploy
    # time, run the bootstrap, then unset it. Unset means the endpoint is
    # disabled (every request is a 503).
    bootstrap_token: SecretStr | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached `Settings` instance.

    Tests can override behavior by clearing the cache:
        get_settings.cache_clear()
    """
    return Settings()
