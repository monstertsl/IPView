from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from app.models.user.user_model import UserRole, AuthMode


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    role: UserRole = UserRole.user
    auth_mode: AuthMode = AuthMode.PASSWORD_ONLY


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserUpdate(BaseModel):
    role: Optional[UserRole] = None
    auth_mode: Optional[AuthMode] = None
    is_active: Optional[bool] = None


class UserPasswordUpdate(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserResponse(UserBase):
    id: str
    is_active: bool
    failed_login_attempts: int
    last_login_at: Optional[datetime]
    totp_enabled: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    user_id: str
    username: str
    role: str
    exp: int
    jti: str


class TOTPEnableResponse(BaseModel):
    secret: str
    uri: str
    qr_image: str


class TOTPVerifyRequest(BaseModel):
    code: str
