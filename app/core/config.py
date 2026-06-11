"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized runtime settings for API, database, and security values.

    These defaults are intentionally development-friendly. Production settings
    are expected to override them through environment variables or secret
    managers instead of editing source code.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "UtterAI Functional Backend"
    app_version: str = "0.1.0"
    api_prefix: str = "/api/v1"

    db_user: str = "utterai"
    db_password: str = "utterai"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "utterai"
    db_pool_size: int = 5
    db_max_overflow: int = 10

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_tls_enabled: bool = False

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14

    internal_callback_token: str = "change-me-internal-token"
    internal_callback_hmac_secret: str = "change-me-hmac-secret"

    aws_region: str = "ap-northeast-2"
    raw_audio_bucket: str = "utterai-raw-audio"
    template_bucket: str = "utterai-templates"
    presigned_url_expire_seconds: int = 900

    sqs_audio_preprocess_queue_url: str = ""
    public_api_base_url: str = "http://localhost:8000"

    otel_service_name: str = "backend"
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    otel_exporter_otlp_protocol: str = "http/protobuf"
    otel_metrics_exporter: str = "otlp"
    otel_traces_exporter: str = "otlp"
    otel_logs_exporter: str = "none"
    otel_resource_attributes: str = "deployment.environment=local,team=utterai"

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    """Cache settings so each process builds the object only once."""

    return Settings()
