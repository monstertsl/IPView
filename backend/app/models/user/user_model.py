import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    user = "user"


class AuthMode(str, enum.Enum):
    PASSWORD_ONLY = "PASSWORD_ONLY"
    TOTP_ONLY = "TOTP_ONLY"
    PASSWORD_AND_TOTP = "PASSWORD_AND_TOTP"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    totp_secret_encrypted: Mapped[str] = mapped_column(String(255), nullable=True)

    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.user, nullable=False)
    auth_mode: Mapped[AuthMode] = mapped_column(SAEnum(AuthMode), default=AuthMode.PASSWORD_ONLY, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_login_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now(), nullable=False
    )
