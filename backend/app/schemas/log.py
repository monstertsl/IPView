from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


class LoginLogResponse(BaseModel):
    id: str
    username: str
    success: bool
    ip_address: Optional[str]
    user_agent: Optional[str]
    message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class LoginLogQuery(BaseModel):
    username: Optional[str] = None
    success: Optional[bool] = None
    ip_address: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ScanLogQuery(BaseModel):
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class CleanupRequest(BaseModel):
    type: Literal["login", "scan"]
    days: int = Field(default=30, ge=1, le=365)


class CleanupResponse(BaseModel):
    deleted_count: int
    message: str
