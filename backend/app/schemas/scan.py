from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.models.scan.scan_model import TaskStatus, TriggerType


class ScanConfigUpdate(BaseModel):
    online_days: int = Field(default=7, ge=1, le=365)
    offline_days: int = Field(default=15, ge=1, le=365)
    cleanup_days: int = Field(default=30, ge=1, le=365)
    snmp_timeout: int = Field(default=3, ge=1, le=60)
    snmp_retry: int = Field(default=2, ge=0, le=10)


class ScanTaskResponse(BaseModel):
    id: str
    status: TaskStatus
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    duration: Optional[int]
    total_ips: int
    updated_ips: int
    error_message: Optional[str]
    triggered_by: TriggerType
    created_at: datetime

    class Config:
        from_attributes = True


class ScanLogResponse(BaseModel):
    id: str
    task_id: str
    status: str
    message: Optional[str]
    duration: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
