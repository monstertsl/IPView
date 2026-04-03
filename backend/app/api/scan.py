from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models.scan.scan_model import ScanTask, ScanLog, TaskStatus, TriggerType
from app.models.switch.switch_model import Switch
from app.models.system.system_model import SystemConfig
from app.schemas.scan import ScanConfigUpdate, ScanTaskResponse, ScanLogResponse
from app.schemas.log import CleanupRequest, CleanupResponse
from app.schemas.system import SystemConfigResponse
from app.tasks.scan import run_scan_task
from datetime import datetime

router = APIRouter(prefix="/api/scan", tags=["扫描管理"])


@router.get("/config", response_model=SystemConfigResponse)
async def get_scan_config(db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
    result = await db.execute(select(SystemConfig).limit(1))
    cfg = result.scalar_one_or_none()
    if not cfg:
        cfg = SystemConfig()
        db.add(cfg)
        await db.commit()
        await db.refresh(cfg)
    return cfg


@router.patch("/config", response_model=SystemConfigResponse)
async def update_scan_config(body: ScanConfigUpdate, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
    result = await db.execute(select(SystemConfig).limit(1))
    cfg = result.scalar_one_or_none()
    if not cfg:
        cfg = SystemConfig()
        db.add(cfg)
    cfg.online_days = body.online_days
    cfg.offline_days = body.offline_days
    cfg.cleanup_days = body.cleanup_days
    await db.commit()
    await db.refresh(cfg)
    return cfg


@router.get("/tasks", response_model=List[ScanTaskResponse])
async def list_tasks(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    result = await db.execute(select(ScanTask).order_by(ScanTask.created_at.desc()).limit(limit))
    tasks = result.scalars().all()
    return [ScanTaskResponse(
        id=str(t.id), status=t.status, started_at=t.started_at,
        finished_at=t.finished_at, duration=t.duration,
        total_ips=t.total_ips, updated_ips=t.updated_ips,
        error_message=t.error_message, triggered_by=t.triggered_by,
        created_at=t.created_at
    ) for t in tasks]


@router.post("/tasks/{task_id}/run")
async def trigger_scan(task_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
    result = await db.execute(select(ScanTask).where(ScanTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    # Enqueue Celery task
    run_scan_task.delay(str(task.id))
    return {"message": "Scan task enqueued", "task_id": task_id}


@router.post("/tasks/now")
async def scan_now(db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
    # Get all active switches
    result = await db.execute(select(Switch).where(Switch.is_active == True))
    switches = result.scalars().all()
    if not switches:
        raise HTTPException(status_code=400, detail="No active switches configured")

    # Create a new scan task
    task = ScanTask(triggered_by=TriggerType.MANUAL)
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # Trigger async scan
    run_scan_task.delay(str(task.id))
    return {"message": "Scan started", "task_id": str(task.id)}


@router.get("/logs", response_model=List[ScanLogResponse])
async def list_scan_logs(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    result = await db.execute(select(ScanLog).order_by(ScanLog.created_at.desc()).limit(limit))
    logs = result.scalars().all()
    return [ScanLogResponse(
        id=str(l.id), task_id=str(l.task_id), status=l.status,
        message=l.message, duration=l.duration, created_at=l.created_at
    ) for l in logs]
