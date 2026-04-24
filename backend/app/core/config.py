from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "IPVIEW"
    DEBUG: bool = False
    # Security-critical: must be supplied via env / docker-compose / .env.
    # No default — application refuses to start if missing or too weak,
    # so a misconfigured deployment can never silently fall back to a
    # well-known key and forge JWTs or decrypt TOTP/SNMP secrets.
    SECRET_KEY: str = Field(..., min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ipview"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Encryption key for TOTP / SNMP community / SNMPv3 secrets.
    # Same rules as SECRET_KEY: must be supplied, no default fallback.
    ENCRYPT_KEY: str = Field(..., min_length=32)

    # System Config defaults
    ONLINE_DAYS: int = 7
    CLEANUP_DAYS: int = 30
    LOGIN_FAIL_LIMIT: int = 5
    INACTIVE_DAYS_LIMIT: int = 90
    LOG_RETENTION_DAYS_LOGIN: int = 90
    LOG_RETENTION_DAYS_SCAN: int = 30

    # SNMP defaults
    SNMP_TIMEOUT: int = 3
    SNMP_RETRY: int = 2

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
