import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
import enum


class SNMPVersion(str, enum.Enum):
    v1 = "v1"
    v2c = "v2c"
    v3 = "v3"


class Switch(Base):
    __tablename__ = "switches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip: Mapped[str] = mapped_column(INET, unique=True, nullable=False, index=True)
    mac: Mapped[str] = mapped_column(String(17), nullable=True)

    snmp_version: Mapped[SNMPVersion] = mapped_column(SAEnum(SNMPVersion), default=SNMPVersion.v2c, nullable=False)
    community: Mapped[str] = mapped_column(String(100), nullable=True)
    snmp_v3_config_encrypted: Mapped[str] = mapped_column(Text, nullable=True)

    location: Mapped[str] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now(), nullable=False
    )
