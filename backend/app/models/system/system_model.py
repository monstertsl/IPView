import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SystemConfig(Base):
    __tablename__ = "system_config"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    online_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    cleanup_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    login_fail_limit: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    inactive_days_limit: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    log_retention_days_login: Mapped[int] = mapped_column(Integer, default=90, nullable=False)
    log_retention_days_scan: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    scan_interval: Mapped[str] = mapped_column(String(20), default="every_day", nullable=False)
    scan_time: Mapped[str] = mapped_column(String(10), default="00:00", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow(), nullable=False
    )
