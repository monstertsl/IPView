from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from app.models.ip.ip_model import IPStatus, IPEventType


class IPSubnetBase(BaseModel):
    cidr: str = Field(..., description="网段 CIDR，如 10.10.0.0/24")

    @field_validator("cidr")
    @classmethod
    def validate_cidr(cls, v: str) -> str:
        import ipaddress
        try:
            network = ipaddress.ip_network(v, strict=False)
            if network.num_addresses < 4:
                raise ValueError("Subnet too small (need at least 4 addresses)")
        except ValueError:
            raise ValueError("Invalid CIDR notation")
        return v


class IPSubnetCreate(IPSubnetBase):
    description: Optional[str] = None


class IPSubnetResponse(IPSubnetBase):
    id: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class IPRecordResponse(BaseModel):
    id: Optional[str] = None
    ip_address: str
    mac_address: Optional[str] = None
    last_seen: Optional[datetime] = None
    status: Optional[IPStatus] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class IPHistoryResponse(BaseModel):
    id: str
    ip_address: str
    mac_address: str
    event_type: IPEventType
    seen_at: datetime

    class Config:
        from_attributes = True


class IPTooltipData(BaseModel):
    ip_address: str
    status: str
    current_mac: Optional[str]
    last_seen: Optional[datetime]
    history: List[IPHistoryResponse]


class IPBulkResponse(BaseModel):
    subnet: str
    total: int
    online: int
    offline: int
    unused: int
    records: List[IPRecordResponse]
