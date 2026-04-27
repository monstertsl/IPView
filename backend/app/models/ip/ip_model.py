import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import Mapped, mapped_column
import enum
from app.core.database import Base


class IPStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    UNUSED = "UNUSED"


class IPEventType(str, enum.Enum):
    NEW = "NEW"
    MAC_CHANGED = "MAC_CHANGED"
    # Emitted when an IP transitions to UNUSED and its mac_address is cleared.
    # The event captures which MAC last occupied this IP before release.
    IP_RELEASED = "IP_RELEASED"


class IPSubnet(Base):
    __tablename__ = "ip_subnets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cidr: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.utcnow(), nullable=False)


class IPRecord(Base):
    __tablename__ = "ip_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_address: Mapped[str] = mapped_column(INET, unique=True, nullable=False, index=True)
    mac_address: Mapped[str] = mapped_column(String(17), nullable=True, index=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[IPStatus] = mapped_column(SAEnum(IPStatus), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow(), nullable=False
    )


class IPEvent(Base):
    __tablename__ = "ip_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_address: Mapped[str] = mapped_column(INET, nullable=False, index=True)
    mac_address: Mapped[str] = mapped_column(String(17), nullable=False)
    event_type: Mapped[IPEventType] = mapped_column(SAEnum(IPEventType), nullable=False)
    seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.utcnow(), nullable=False, index=True)
