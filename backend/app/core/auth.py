from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid

from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
import pyotp
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.redis import RedisSession, get_redis
from app.core.rate_limit import (
    get_cached_user_status,
    set_cached_user_status,
    invalidate_user_status,  # re-export
)
from app.models.user.user_model import User, AuthMode, UserRole
from app.schemas.user import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Sliding-session refresh threshold (M2): re-issue token when remaining lifetime is smaller.
REFRESH_THRESHOLD_SECONDS = 10 * 60


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4())})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return TokenData(
            user_id=payload.get("sub"),
            username=payload.get("username"),
            role=payload.get("role"),
            exp=payload.get("exp"),
            jti=payload.get("jti"),
        )
    except JWTError:
        return None


class AuthContext:
    """Authenticated request context with authoritative DB-backed state."""

    def __init__(
        self,
        token_data: TokenData,
        role: str,
        is_active: bool,
        auth_mode: str,
    ):
        # Keep TokenData-compatible attributes so existing call sites continue to work.
        self.user_id: str = token_data.user_id
        self.username: str = token_data.username
        self.role: str = role  # authoritative role from DB
        self.exp: int = token_data.exp
        self.jti: str = token_data.jti
        self.is_active: bool = is_active
        self.auth_mode: str = auth_mode


async def _load_user_status(user_id: str, db: AsyncSession) -> Optional[dict]:
    """Return {'role','is_active','auth_mode'} from cache or DB, or None if not found."""
    cached = await get_cached_user_status(user_id)
    if cached:
        return cached

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None
    payload = {
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        "is_active": bool(user.is_active),
        "auth_mode": user.auth_mode.value if hasattr(user.auth_mode, "value") else str(user.auth_mode),
    }
    await set_cached_user_status(user_id, payload)
    return payload


async def _maybe_refresh_token(ctx: AuthContext, response: Optional[Response]) -> None:
    """Slide the session if token is close to expiry (M2)."""
    if response is None:
        return
    now_ts = int(datetime.now(timezone.utc).timestamp())
    remaining = (ctx.exp or 0) - now_ts
    if remaining <= 0 or remaining >= REFRESH_THRESHOLD_SECONDS:
        return

    new_token = create_access_token({
        "sub": ctx.user_id,
        "username": ctx.username,
        "role": ctx.role,
    })
    response.headers["X-Refreshed-Token"] = new_token
    response.headers["Access-Control-Expose-Headers"] = "X-Refreshed-Token"

    # Cache the new session id so logout/blacklist can find it.
    new_td = decode_token(new_token)
    if new_td is not None:
        await RedisSession.set(
            f"session:{new_td.jti}",
            {"user_id": ctx.user_id, "username": ctx.username, "role": ctx.role},
            expire=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )


async def get_current_user(
    response: Response,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    """Decode JWT, validate against DB/cache, and optionally slide the session."""
    token = credentials.credentials
    token_data = decode_token(token)
    if token_data is None or not token_data.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    # Blacklist check.
    blacklisted = await RedisSession.get(f"token:blacklist:{token_data.jti}")
    if blacklisted:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

    # Authoritative user status.
    status_info = await _load_user_status(token_data.user_id, db)
    if not status_info:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    if not status_info.get("is_active", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    ctx = AuthContext(
        token_data=token_data,
        role=status_info.get("role") or token_data.role,
        is_active=status_info.get("is_active", False),
        auth_mode=status_info.get("auth_mode") or "",
    )

    await _maybe_refresh_token(ctx, response)
    return ctx


def require_role(required_role: str):
    async def role_checker(current_user: AuthContext = Depends(get_current_user)):
        if required_role == "admin" and current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
        return current_user
    return role_checker


def verify_totp(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(secret: str, username: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=settings.APP_NAME)


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_token",
    "get_current_user",
    "require_role",
    "verify_totp",
    "generate_totp_secret",
    "get_totp_uri",
    "AuthContext",
    "invalidate_user_status",
]
