import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Enum as SAEnum, Index
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
import enum


class IPStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    UNUSED = "UNUSED"


class IPEventType(str, enum.Enum):
    NEW = "NEW"
    MAC_CHANGED = "MAC_CHANGED"


class IPSubnet(Base):
    __tablename__ = "ip_subnets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cidr: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(), nullable=False)


class IPRecord(Base):
    __tablename__ = "ip_records"
    __table_args__ = (
        Index("ix_ip_records_ip_address", "ip_address", postgresql_using="btree"),
        Index("ix_ip_records_mac_address", "mac_address", postgresql_using="btree"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_address: Mapped[str] = mapped_column(INET, unique=True, nullable=False, index=True)
    mac_address: Mapped[str] = mapped_column(String(17), nullable=True, index=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[IPStatus] = mapped_column(SAEnum(IPStatus), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now(), nullable=False
    )


class IPEvent(Base):
    __tablename__ = "ip_events"
    __table_args__ = (
        Index("ix_ip_events_ip_address", "ip_address"),
        Index("ix_ip_events_seen_at", "seen_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_address: Mapped[str] = mapped_column(INET, nullable=False, index=True)
    mac_address: Mapped[str] = mapped_column(String(17), nullable=False)
    event_type: Mapped[IPEventType] = mapped_column(SAEnum(IPEventType), nullable=False)
    seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(), nullable=False)
