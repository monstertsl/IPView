from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SystemLogResponse(BaseModel):
    id: str
    action: str
    target_type: str
    target_id: Optional[str]
    detail: Optional[str]
    operator: Optional[str]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
