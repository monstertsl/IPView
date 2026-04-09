from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List

from app.core.database import get_db
from app.core.auth import (
    hash_password, verify_password, generate_totp_secret,
    get_totp_uri, verify_totp, get_current_user, require_role
)
from app.core.security import encrypt_data, decrypt_data
from app.models.user.user_model import User, AuthMode
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserPasswordUpdate, AdminPasswordReset,
    TOTPEnableResponse, TOTPVerifyRequest
)

router = APIRouter(prefix="/api/users", tags=["用户管理"])


def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        username=user.username,
        role=user.role,
        auth_mode=user.auth_mode,
        is_active=user.is_active,
        failed_login_attempts=user.failed_login_attempts,
        last_login_at=user.last_login_at,
        totp_enabled=bool(user.totp_secret_encrypted),
        created_at=user.created_at,
    )


@router.get("", response_model=List[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [_user_to_response(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_to_response(user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
    result = await db.execute(select(User).where(User.username == body.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    
    # 根据认证模式处理密码
    if body.auth_mode == AuthMode.TOTP_ONLY:
        # 仅 TOTP 模式：生成随机密码哈希（不会使用）
        import secrets
        password_hash = hash_password(secrets.token_hex(32))
    else:
        if not body.password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password required for this auth mode")
        password_hash = hash_password(body.password)
    
    user = User(
        username=body.username,
        password_hash=password_hash,
        role=body.role,
        auth_mode=body.auth_mode,
    )
    
    # 如果是 TOTP 相关模式，自动生成 TOTP 密钥
    if body.auth_mode in (AuthMode.TOTP_ONLY, AuthMode.PASSWORD_AND_TOTP):
        secret = generate_totp_secret()
        user.totp_secret_encrypted = encrypt_data(secret)
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _user_to_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, body: UserUpdate, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if body.role is not None:
        user.role = body.role
    if body.auth_mode is not None:
        user.auth_mode = body.auth_mode
    if body.is_active is not None:
        user.is_active = body.is_active
    await db.commit()
    await db.refresh(user)
    return _user_to_response(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await db.delete(user)
    await db.commit()


@router.post("/{user_id}/password", status_code=status.HTTP_200_OK)
async def change_password(user_id: str, body: UserPasswordUpdate, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    # Users can change own password, admin can change any
    if str(current_user.user_id) != user_id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old password incorrect")
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"message": "Password updated"}


@router.post("/{user_id}/totp/enable", response_model=TOTPEnableResponse)
async def enable_totp(user_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if str(current_user.user_id) != user_id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    secret = generate_totp_secret()
    user.totp_secret_encrypted = encrypt_data(secret)
    user.auth_mode = AuthMode.PASSWORD_AND_TOTP
    await db.commit()

    uri = get_totp_uri(secret, user.username)
    return TOTPEnableResponse(secret=secret, uri=uri, qr_image=uri)


@router.post("/{user_id}/totp/disable")
async def disable_totp(user_id: str, body: TOTPVerifyRequest, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    if str(current_user.user_id) != user_id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.totp_secret_encrypted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP not enabled")
    secret = decrypt_data(user.totp_secret_encrypted)
    if not verify_totp(secret, body.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid TOTP code")
    user.totp_secret_encrypted = None
    user.auth_mode = AuthMode.PASSWORD_ONLY
    await db.commit()
    return {"message": "TOTP disabled"}


@router.get("/{user_id}/totp/secret")
async def get_totp_secret(user_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
    """Admin can view user's TOTP secret (for manual entry into authenticator apps)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.totp_secret_encrypted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP not enabled")
    secret = decrypt_data(user.totp_secret_encrypted)
    uri = get_totp_uri(secret, user.username)
    return {"secret": secret, "uri": uri}


@router.put("/{user_id}/password/reset")
async def admin_reset_password(user_id: str, body: AdminPasswordReset, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
    """Admin can directly reset user's password without knowing the old password."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"message": "密码已重置"}


@router.post("/{user_id}/totp/reset", response_model=TOTPEnableResponse)
async def reset_totp(user_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
    """Admin can reset user's TOTP secret — generates a new key and discards the old one."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    secret = generate_totp_secret()
    user.totp_secret_encrypted = encrypt_data(secret)
    if user.auth_mode == AuthMode.PASSWORD_ONLY:
        user.auth_mode = AuthMode.PASSWORD_AND_TOTP
    await db.commit()

    uri = get_totp_uri(secret, user.username)
    return TOTPEnableResponse(secret=secret, uri=uri, qr_image=uri)
