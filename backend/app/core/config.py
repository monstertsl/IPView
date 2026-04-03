from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "IPVIEW"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-use-strong-random-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ipview"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Encryption key for TOTP/SNMPv3 secrets (32 bytes hex)
    ENCRYPT_KEY: str = "0" * 64

    # System Config defaults
    ONLINE_DAYS: int = 7
    OFFLINE_DAYS: int = 15
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
