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

    database_url: str = (
        "postgresql+psycopg://utterai:utterai@localhost:5432/utterai"
    )

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14

    internal_callback_token: str = "change-me-internal-token"
    internal_callback_hmac_secret: str = "change-me-hmac-secret"


@lru_cache
def get_settings() -> Settings:
    """Cache settings so each process builds the object only once."""

    return Settings()
