from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.auth import (
    hash_password, verify_password, create_access_token,
    verify_totp, generate_totp_secret, get_totp_uri, decode_token, get_current_user, require_role
)
from app.core.redis import RedisSession
from app.core.security import encrypt_data, decrypt_data
from app.core.config import settings
from app.models.user.user_model import User, UserRole, AuthMode
from app.models.log.log_model import LoginLog
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserPasswordUpdate,
    LoginRequest, LoginResponse, TOTPEnableResponse, TOTPVerifyRequest
)

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Lookup user
    result = await db.execute(select(User).where(User.username == body.username))
    user: User = result.scalar_one_or_none()

    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "")

    if not user:
        # Log failed attempt
        login_log = LoginLog(
            username=body.username, success=False,
            ip_address=client_ip, user_agent=user_agent,
            message="User not found"
        )
        db.add(login_log)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Check if user is active
    if not user.is_active:
        login_log = LoginLog(
            username=body.username, success=False,
            ip_address=client_ip, user_agent=user_agent,
            message="Account is disabled"
        )
        db.add(login_log)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    # Verify password
    if not verify_password(body.password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.LOGIN_FAIL_LIMIT:
            user.is_active = False
        login_log = LoginLog(
            username=body.username, success=False,
            ip_address=client_ip, user_agent=user_agent,
            message=f"Wrong password (attempt {user.failed_login_attempts})"
        )
        db.add(login_log)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Check auth_mode
    if user.auth_mode in (AuthMode.TOTP_ONLY, AuthMode.PASSWORD_AND_TOTP):
        if not body.totp_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP code required")
        if not user.totp_secret_encrypted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP not configured")
        secret = decrypt_data(user.totp_secret_encrypted)
        if not verify_totp(secret, body.totp_code):
            user.failed_login_attempts += 1
            login_log = LoginLog(
                username=body.username, success=False,
                ip_address=client_ip, user_agent=user_agent,
                message=f"Wrong TOTP code (attempt {user.failed_login_attempts})"
            )
            db.add(login_log)
            await db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid TOTP code")

    # Success
    user.failed_login_attempts = 0
    user.last_login_at = datetime.now(timezone.utc)
    login_log = LoginLog(
        username=body.username, success=True,
        ip_address=client_ip, user_agent=user_agent,
        message="Login successful"
    )
    db.add(login_log)
    await db.commit()

    # Create token
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.value
    }
    access_token = create_access_token(token_data)
    token_data_decoded = decode_token(access_token)

    # Cache session
    await RedisSession.set(
        f"session:{token_data_decoded.jti}",
        {"user_id": str(user.id), "username": user.username, "role": user.role.value},
        expire=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    return LoginResponse(
        access_token=access_token,
        user=UserResponse(
            id=str(user.id),
            username=user.username,
            role=user.role,
            auth_mode=user.auth_mode,
            is_active=user.is_active,
            failed_login_attempts=user.failed_login_attempts,
            last_login_at=user.last_login_at,
            totp_enabled=bool(user.totp_secret_encrypted),
            created_at=user.created_at
        )
    )


@router.post("/logout")
async def logout(current_user=Depends(get_current_user)):
    # Blacklist current token
    await RedisSession.delete(f"session:{current_user.jti}")
    return {"message": "Logged out successfully"}


@router.post("/register", response_model=UserResponse)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check duplicate
    result = await db.execute(select(User).where(User.username == body.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role,
        auth_mode=body.auth_mode,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse(
        id=str(user.id), username=user.username, role=user.role,
        auth_mode=user.auth_mode, is_active=user.is_active,
        failed_login_attempts=0, last_login_at=None,
        totp_enabled=False, created_at=user.created_at
    )
