from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Any
from datetime import datetime
from app.models.switch.switch_model import SNMPVersion


class SNMPv3Config(BaseModel):
    username: str
    auth_protocol: str = "SHA"  # SHA | MD5
    auth_password: str
    priv_protocol: str = "AES"  # AES | DES
    priv_password: str


class SwitchBase(BaseModel):
    ip: str = Field(..., description="交换机 IP 地址")
    mac: Optional[str] = Field(None, description="MAC 地址")
    snmp_version: SNMPVersion = SNMPVersion.v2c
    community: Optional[str] = Field(None, max_length=100)
    snmp_v3_config: Optional[SNMPv3Config] = None
    location: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=255)

    @model_validator(mode="after")
    def check_snmp_config(self):
        if self.snmp_version in (SNMPVersion.v1, SNMPVersion.v2c) and not self.community:
            raise ValueError("Community string is required for SNMP v1/v2c")
        if self.snmp_version == SNMPVersion.v3 and not self.snmp_v3_config:
            raise ValueError("SNMPv3 config is required for SNMP v3")
        return self

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        import ipaddress
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError("Invalid IP address")
        return v

    @field_validator("mac")
    @classmethod
    def validate_mac(cls, v: Optional[str]) -> Optional[str]:
        if v:
            import re
            # Accept both : and - as separators
            if not re.match(r"^[0-9A-Fa-f]{2}([:-])[0-9A-Fa-f]{2}(\1[0-9A-Fa-f]{2}){4}$", v):
                raise ValueError("Invalid MAC address format (expected XX:XX:XX:XX:XX:XX)")
            # Normalize to : separator
            v = v.upper().replace("-", ":")
        return v


class SwitchCreate(SwitchBase):
    pass


class SwitchUpdate(BaseModel):
    mac: Optional[str] = None
    snmp_version: Optional[SNMPVersion] = None
    community: Optional[str] = None
    snmp_v3_config: Optional[SNMPv3Config] = None
    location: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SwitchResponse(SwitchBase):
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
