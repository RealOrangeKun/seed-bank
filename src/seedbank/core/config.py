"""Application settings.

The single source of truth for environment-driven configuration.
Anything that varies between dev / staging / prod lives here and only here.
Code that needs a setting receives it via the `Settings` object — never via
`os.environ`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Service identity ─────────────────────────────────────────────────────
    env: Literal["dev", "test", "staging", "prod"] = "dev"
    service_name: str = "seedbank-api"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    debug: bool = False

    # ── HTTP ─────────────────────────────────────────────────────────────────
    api_v1_prefix: str = "/api/v1"
    cors_allow_origins: list[str] = Field(default_factory=list)
    trusted_hosts: list[str] = Field(default_factory=lambda: ["*"])

    # ── Auth ─────────────────────────────────────────────────────────────────
    jwt_secret: SecretStr = SecretStr("change-me-in-prod")  # noqa: S106
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_seconds: int = 60 * 15           # 15 min
    jwt_refresh_ttl_seconds: int = 60 * 60 * 24 * 7  # 7 days
    bcrypt_rounds: int = 12
    api_key_prefix: str = "seedbank_"

    # OAuth (filled in via env in prod)
    oauth_google_client_id: SecretStr | None = None
    oauth_google_client_secret: SecretStr | None = None
    oauth_github_client_id: SecretStr | None = None
    oauth_github_client_secret: SecretStr | None = None
    oauth_redirect_base_url: str = "http://localhost:8000"

    # ── Postgres ─────────────────────────────────────────────────────────────
    postgres_dsn: PostgresDsn = Field(
        default="postgresql+asyncpg://seedbank:seedbank@postgres:5432/seedbank"  # type: ignore[arg-type]
    )
    postgres_pool_size: int = 10
    postgres_max_overflow: int = 5
    postgres_pool_timeout: int = 30
    postgres_echo: bool = False

    # ── Redis ────────────────────────────────────────────────────────────────
    redis_dsn: RedisDsn = Field(default="redis://redis:6379/0")  # type: ignore[arg-type]

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

    # ── ClickHouse ───────────────────────────────────────────────────────────
    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = 8123
    clickhouse_user: str = "seedbank"
    clickhouse_password: SecretStr = SecretStr("seedbank-dev-secret")
    clickhouse_database: str = "seedbank"

    # ── MLflow ───────────────────────────────────────────────────────────────
    mlflow_tracking_uri: str = "http://mlflow:5000"
    mlflow_experiment_name: str = "seedbank"

    # ── Inference ────────────────────────────────────────────────────────────
    inference_default_backend: Literal["torch_local", "roboflow", "ultralytics_yolo"] = (
        "torch_local"
    )
    roboflow_api_key: SecretStr | None = None
    inference_max_image_bytes: int = 10 * 1024 * 1024
    inference_max_image_pixels: int = 4096 * 4096

    # ── Observability ────────────────────────────────────────────────────────
    otel_exporter_otlp_endpoint: str | None = None
    sentry_dsn: SecretStr | None = None
    enable_metrics: bool = True

    # ── Rate limiting ────────────────────────────────────────────────────────
    rate_limit_per_minute: int = 120


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached `Settings` instance.

    Tests can override behavior by clearing the cache:
        get_settings.cache_clear()
    """
    return Settings()
