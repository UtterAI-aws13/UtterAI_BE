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

    ai_service_base_url: str = ""
    ai_service_analysis_path: str = "/internal/ai/analysis-jobs"
    public_api_base_url: str = "http://localhost:8000"

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    """Cache settings so each process builds the object only once."""

    return Settings()
