from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.core.database import get_db
from app.core.auth import (
    hash_password, verify_password, create_access_token,
    verify_totp, decode_token, get_current_user, require_role,
    invalidate_user_status,
)
from app.core.redis import RedisSession, get_redis
from app.core.security import decrypt_data
from app.core.config import settings
from app.core.rate_limit import (
    check_auth_ip_limit,
    check_auth_user_limit,
    record_auth_failure,
    reset_auth_counters,
)
from app.models.user.user_model import User, AuthMode
from app.models.log.log_model import LoginLog
from app.schemas.user import (
    UserCreate, UserResponse,
    LoginRequest, LoginResponse,
    CheckUserRequest, CheckUserResponse,
)

router = APIRouter(prefix="/api/auth", tags=["认证"])

# Unified auth-failure message (M3): do not leak whether the user exists.
GENERIC_AUTH_FAILURE = "用户名或口令错误"


def _extract_client_ip(request: Request) -> str:
    return (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or request.headers.get("x-real-ip", "")
        or (request.client.host if request.client else "unknown")
    )


def _rate_limit_response(retry_after: int) -> HTTPException:
    headers = {"Retry-After": str(max(int(retry_after), 1))}
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="请求过于频繁，请稍后再试",
        headers=headers,
    )


@router.post("/check-user", response_model=CheckUserResponse)
async def check_user(
    body: CheckUserRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Check user existence/auth mode.

    H4: IP-level rate limit + uniform response so attackers cannot enumerate users.
    """
    client_ip = _extract_client_ip(request)

    # IP rate limit (shared with /login).
    allowed, retry_after = await check_auth_ip_limit(client_ip)
    if not allowed:
        raise _rate_limit_response(retry_after)

    result = await db.execute(select(User).where(User.username == body.username))
    user: User = result.scalar_one_or_none()

    if not user:
        # Pretend the user exists with the most common auth mode so responses are indistinguishable.
        return CheckUserResponse(
            exists=True,
            auth_mode=AuthMode.PASSWORD_ONLY.value,
            totp_enabled=False,
        )

    return CheckUserResponse(
        exists=True,
        auth_mode=user.auth_mode.value,
        totp_enabled=bool(user.totp_secret_encrypted),
    )


async def _record_failed_login(
    user: User,
    db: AsyncSession,
    *,
    username: str,
    client_ip: str,
    user_agent: str,
    reason: str,
) -> None:
    """Unified failed-login bookkeeping (H2, M3).

    - Increments per-user failed_login_attempts and disables the account on the limit.
    - Writes audit log with the real reason (for ops).
    - Updates Redis IP/username rate-limit counters.
    - Invalidates the user-status cache so disable takes effect immediately.
    """
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= settings.LOGIN_FAIL_LIMIT:
        user.is_active = False

    login_log = LoginLog(
        username=username,
        success=False,
        ip_address=client_ip,
        user_agent=user_agent,
        message=f"{reason} (attempt {user.failed_login_attempts})",
    )
    db.add(login_log)
    await db.commit()

    # Invalidate user-status cache so the next request sees the new state.
    await invalidate_user_status(str(user.id))
    # Rate-limit counters.
    await record_auth_failure(client_ip, username)


@router.post("/login", response_model=LoginResponse)
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    client_ip = _extract_client_ip(request)
    user_agent = request.headers.get("user-agent", "")

    # Rate limit (M3 + shared IP with H4).
    allowed, retry_after = await check_auth_ip_limit(client_ip)
    if not allowed:
        raise _rate_limit_response(retry_after)
    allowed, retry_after = await check_auth_user_limit(body.username)
    if not allowed:
        raise _rate_limit_response(retry_after)

    # Lookup user.
    result = await db.execute(select(User).where(User.username == body.username))
    user: User = result.scalar_one_or_none()

    if not user:
        # No user record to mutate, but still count the failure for IP/username to block probing.
        db.add(LoginLog(
            username=body.username, success=False,
            ip_address=client_ip, user_agent=user_agent,
            message="User not found",
        ))
        await db.commit()
        await record_auth_failure(client_ip, body.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_AUTH_FAILURE)

    if not user.is_active:
        db.add(LoginLog(
            username=body.username, success=False,
            ip_address=client_ip, user_agent=user_agent,
            message="Account is disabled",
        ))
        await db.commit()
        # Account disabled is a distinct 403 so the user knows to contact admin.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")

    # Authenticate according to mode.
    if user.auth_mode == AuthMode.TOTP_ONLY:
        if not body.totp_code:
            return JSONResponse(
                status_code=400,
                content={"detail": "需要TOTP验证码", "need_totp": True, "auth_mode": user.auth_mode.value},
            )
        if not user.totp_secret_encrypted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP未配置，请联系管理员")
        secret = decrypt_data(user.totp_secret_encrypted)
        if not verify_totp(secret, body.totp_code):
            await _record_failed_login(
                user, db,
                username=body.username, client_ip=client_ip,
                user_agent=user_agent, reason="Wrong TOTP code",
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_AUTH_FAILURE)

    elif user.auth_mode == AuthMode.PASSWORD_ONLY:
        if not body.password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请输入密码")
        if not verify_password(body.password, user.password_hash):
            await _record_failed_login(
                user, db,
                username=body.username, client_ip=client_ip,
                user_agent=user_agent, reason="Wrong password",
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_AUTH_FAILURE)

    elif user.auth_mode == AuthMode.PASSWORD_AND_TOTP:
        if not body.password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请输入密码")
        if not verify_password(body.password, user.password_hash):
            await _record_failed_login(
                user, db,
                username=body.username, client_ip=client_ip,
                user_agent=user_agent, reason="Wrong password",
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_AUTH_FAILURE)

        if not body.totp_code:
            return JSONResponse(
                status_code=400,
                content={"detail": "需要TOTP验证码", "need_totp": True, "auth_mode": user.auth_mode.value},
            )
        if not user.totp_secret_encrypted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP未配置，请联系管理员")
        secret = decrypt_data(user.totp_secret_encrypted)
        if not verify_totp(secret, body.totp_code):
            await _record_failed_login(
                user, db,
                username=body.username, client_ip=client_ip,
                user_agent=user_agent, reason="Wrong TOTP code",
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=GENERIC_AUTH_FAILURE)

    # Success path.
    user.failed_login_attempts = 0
    user.last_login_at = datetime.utcnow()
    db.add(LoginLog(
        username=body.username, success=True,
        ip_address=client_ip, user_agent=user_agent,
        message="Login successful",
    ))
    await db.commit()

    # Invalidate and rebuild user-status cache.
    await invalidate_user_status(str(user.id))
    # Reset rate counters on success.
    await reset_auth_counters(client_ip, body.username)

    # Create token.
    access_token = create_access_token({
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.value,
    })
    token_data_decoded = decode_token(access_token)

    await RedisSession.set(
        f"session:{token_data_decoded.jti}",
        {"user_id": str(user.id), "username": user.username, "role": user.role.value},
        expire=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
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
            created_at=user.created_at,
        ),
    )


@router.post("/logout")
async def logout(current_user=Depends(get_current_user)):
    """Revoke the caller's token (M1 backend-side)."""
    remaining_ttl = max(current_user.exp - int(__import__("time").time()), 60)
    r = await get_redis()
    await r.setex(f"token:blacklist:{current_user.jti}", remaining_ttl, "1")
    await RedisSession.delete(f"session:{current_user.jti}")
    # Also clear user-status cache so any later tokens re-check DB.
    await invalidate_user_status(str(current_user.user_id))
    return {"message": "Logged out successfully"}


@router.post("/register", response_model=UserResponse)
async def register(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin")),
):
    """Register a new user — admin only."""
    result = await db.execute(select(User).where(User.username == body.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")

    if not body.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is required")

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
        totp_enabled=False, created_at=user.created_at,
    )
