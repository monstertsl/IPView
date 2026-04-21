from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import datetime
from app.models.switch.switch_model import SNMPVersion

# Placeholder used to mask secrets in responses.
MASKED_PASSWORD = "******"


class SNMPv3Config(BaseModel):
    username: str
    auth_protocol: str = "SHA"  # SHA | MD5
    auth_password: str
    priv_protocol: str = "AES"  # AES | DES
    priv_password: str


class SNMPv3ConfigUpdate(BaseModel):
    """Incoming SNMPv3 config for updates.

    Passwords are optional; if omitted (or sent as ``******``) the existing stored values are kept.
    """

    username: Optional[str] = None
    auth_protocol: Optional[str] = None
    auth_password: Optional[str] = None
    priv_protocol: Optional[str] = None
    priv_password: Optional[str] = None


class SNMPv3ConfigResponse(BaseModel):
    """Outgoing SNMPv3 config.

    Real passwords are never returned. Clients receive ``******`` when a password is configured,
    so that UI fields can keep placeholder values and explicit "password is set" flags are obvious.
    """

    username: str
    auth_protocol: str = "SHA"
    priv_protocol: str = "AES"
    auth_password: str = MASKED_PASSWORD
    priv_password: str = MASKED_PASSWORD
    auth_password_set: bool = True
    priv_password_set: bool = True


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
            v = v.upper().replace("-", ":")
        return v


class SwitchCreate(SwitchBase):
    pass


class SwitchUpdate(BaseModel):
    mac: Optional[str] = None
    snmp_version: Optional[SNMPVersion] = None
    community: Optional[str] = None
    snmp_v3_config: Optional[SNMPv3ConfigUpdate] = None
    location: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SwitchResponse(BaseModel):
    """Response model for a switch.

    Sensitive fields (SNMP v1/v2c community and SNMPv3 passwords) are never returned in
    plaintext. Clients receive ``******`` when a value is stored, together with a boolean
    ``*_set`` flag that tells the UI whether something is configured.
    """

    id: str
    ip: str
    mac: Optional[str] = None
    snmp_version: SNMPVersion = SNMPVersion.v2c
    community: Optional[str] = None  # always ``******`` when community_set is True
    community_set: bool = False
    snmp_v3_config: Optional[SNMPv3ConfigResponse] = None
    location: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
