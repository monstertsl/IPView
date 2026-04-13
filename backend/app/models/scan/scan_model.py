import uuid
from app.core.database import Base
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
import enum


class TaskStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class TriggerType(str, enum.Enum):
    SYSTEM = "SYSTEM"
    MANUAL = "MANUAL"


class ScanTask(Base):
    __tablename__ = "scan_tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), default=TaskStatus.PENDING, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    duration: Mapped[int] = mapped_column(Integer, nullable=True)

    total_ips: Mapped[int] = mapped_column(Integer, default=0)
    updated_ips: Mapped[int] = mapped_column(Integer, default=0)

    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    triggered_by: Mapped[TriggerType] = mapped_column(SAEnum(TriggerType), default=TriggerType.MANUAL)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.utcnow(), nullable=False)

