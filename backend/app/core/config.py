"""
backend/app/core/config.py
Application settings loaded from environment variables via pydantic-settings.
"""
from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "Adaptive Cloud Security API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # ── API ──────────────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "https://localhost"]

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: PostgresDsn = "postgresql+asyncpg://postgres:postgres@localhost:5432/adaptivecloud"  # type: ignore[assignment]
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False

    # ── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION_USE_32_CHARS_MINIMUM"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── ML Service ───────────────────────────────────────────────────────────
    ML_SERVICE_URL: str = "http://ml-service:8001"
    ML_ALERT_THRESHOLD: float = 0.80       # Min confidence to create an alert
    ML_INFERENCE_ENABLED: bool = True

    # ── Wazuh ────────────────────────────────────────────────────────────────
    WAZUH_API_URL: str = "https://wazuh-manager:55000"
    WAZUH_API_USER: str = "wazuh-wui"
    WAZUH_API_PASSWORD: str = "CHANGE_ME"
    WAZUH_ENABLED: bool = False            # Enable only when Wazuh is running

    # ── Pagination ───────────────────────────────────────────────────────────
    DEFAULT_PAGE_SIZE: int = 100
    MAX_PAGE_SIZE: int = 1000

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        """Accept plain postgres:// and convert to asyncpg driver string."""
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton settings — imported throughout the app."""
    return Settings()
