import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LoginLog(Base):
    __tablename__ = "login_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str] = mapped_column(Text, nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.utcnow(), nullable=False, index=True)
