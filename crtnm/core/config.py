"""Runtime settings loaded exclusively from the environment."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration; secrets must be injected at deployment time."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="CRTNM_", extra="ignore")
    environment: str = "development"
    database_url: str = "sqlite:///./crtnm.db"
    secret_key: str = "unsafe-development-key-change-me"
    fernet_key: str = ""
    cors_origins: str = "http://localhost:5173"
    token_expiry_minutes: int = 60
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    rate_limit_per_minute: int = 10


@lru_cache
def get_settings() -> Settings:
    """Return process-wide immutable settings."""
    return Settings()
