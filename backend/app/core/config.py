"""
backend/app/core/config.py
Application settings configured via pydantic-settings.
Supports both root .env and backend/.env configurations.
"""
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "backend/.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App Info ─────────────────────────────────────────────────────────────
    APP_NAME: str = "AdaptiveCloud Security Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DOMAIN: str = "localhost"

    # ── API Paths & Prefixes ─────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",
        "https://localhost",
        "http://localhost",
    ]

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres_dev_only@postgres:5432/adaptivecloud"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_ECHO: bool = False

    # ── Security & JWT ───────────────────────────────────────────────────────
    # Supports either JWT_SECRET or JWT_SECRET_KEY
    JWT_SECRET: str = "adaptivecloud_development_secret_key_change_in_production_min32chars"
    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Agent Ingest Key ─────────────────────────────────────────────────────
    AGENT_API_KEY: str = "adm-agent-live-insecure-dev-key-change-in-production"

    # ── Wazuh Integration ────────────────────────────────────────────────────
    WAZUH_ALERTS_PATH: str = "/var/ossec/logs/alerts/alerts.json"
    WAZUH_ENABLED: bool = False
    WAZUH_API_URL: str = "https://wazuh-manager:55000"
    WAZUH_API_USER: str = "wazuh-wui"
    WAZUH_API_PASSWORD: str = "CHANGE_ME"

    # ── ML Microservice ──────────────────────────────────────────────────────
    ML_SERVICE_URL: str = "http://ml-service:8001"
    ML_ALERT_THRESHOLD: float = 0.80

    # ── Pagination Defaults ──────────────────────────────────────────────────
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 500

    @property
    def secret_key(self) -> str:
        """Resolve either JWT_SECRET_KEY or JWT_SECRET."""
        return self.JWT_SECRET_KEY or self.JWT_SECRET

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
