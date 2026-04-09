import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScanSubnet(Base):
    """入库网段配置 - 只有匹配这些网段的IP才会被入库"""
    __tablename__ = "scan_subnets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cidr: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow(), nullable=False
    )
