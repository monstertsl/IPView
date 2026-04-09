from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, func
from typing import Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models.log.log_model import LoginLog
from app.models.scan.scan_model import ScanLog
from app.schemas.log import LoginLogResponse, LoginLogQuery, ScanLogQuery, CleanupRequest, CleanupResponse

router = APIRouter(prefix="/api/logs", tags=["日志查询"])


@router.get("/login")
async def list_login_logs(
    username: Optional[str] = None,
    success: Optional[bool] = None,
    ip_address: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    query = select(LoginLog)
    conditions = []
    if username:
        conditions.append(LoginLog.username == username)
    if success is not None:
        conditions.append(LoginLog.success == success)
    if ip_address:
        conditions.append(LoginLog.ip_address == ip_address)
    if start_date:
        conditions.append(LoginLog.created_at >= start_date)
    if end_date:
        conditions.append(LoginLog.created_at <= end_date)

    if conditions:
        query = query.where(and_(*conditions))

    # Count
    count_query = select(func.count()).select_from(LoginLog)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(LoginLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    items = [LoginLogResponse(
        id=str(l.id), username=l.username, success=l.success,
        ip_address=l.ip_address, user_agent=l.user_agent,
        message=l.message, created_at=l.created_at
    ) for l in logs]

    return {"total": total, "page": page, "page_size": page_size, "items": [item.model_dump() for item in items]}


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_logs(
    body: CleanupRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    cutoff = datetime.utcnow() - timedelta(days=body.days)

    if body.type == "login":
        result = await db.execute(
            delete(LoginLog).where(LoginLog.created_at < cutoff)
        )
        deleted = result.rowcount
    else:
        result = await db.execute(
            delete(ScanLog).where(ScanLog.created_at < cutoff)
        )
        deleted = result.rowcount

    await db.commit()
    return CleanupResponse(
        deleted_count=deleted or 0,
        message=f"Deleted {deleted or 0} {body.type} log entries older than {body.days} days"
    )
