from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SystemConfigResponse(BaseModel):
    online_days: int
    cleanup_days: int
    login_fail_limit: int
    inactive_days_limit: int
    log_retention_days_login: int
    log_retention_days_scan: int
    scan_interval: str = "every_day"
    scan_time: str = "00:00"
    updated_at: datetime

    class Config:
        from_attributes = True


class SystemConfigUpdate(BaseModel):
    online_days: int = Field(default=7, ge=1, le=365)
    cleanup_days: int = Field(default=30, ge=1, le=365)
    login_fail_limit: int = Field(default=5, ge=1, le=20)
    inactive_days_limit: int = Field(default=90, ge=7, le=365)
    log_retention_days_login: int = Field(default=90, ge=7, le=365)
    log_retention_days_scan: int = Field(default=30, ge=7, le=365)
    scan_interval: Optional[str] = None
    scan_time: Optional[str] = None


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list
