from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.core.auth import get_current_user, require_role
from app.models.scan.scan_model import ScanTask, TaskStatus, TriggerType
from app.models.scan.scan_subnet_model import ScanSubnet
from app.models.switch.switch_model import Switch
from app.models.system.system_model import SystemConfig
from app.schemas.scan import (
    ScanConfigUpdate, ScanTaskResponse,
    ScanSubnetCreate, ScanSubnetUpdate, ScanSubnetResponse
)
from app.schemas.log import CleanupRequest, CleanupResponse
from app.schemas.system import SystemConfigResponse, SystemConfigUpdate
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
async def update_scan_config(body: SystemConfigUpdate, db: AsyncSession = Depends(get_db), current_user=Depends(require_role("admin"))):
    result = await db.execute(select(SystemConfig).limit(1))
    cfg = result.scalar_one_or_none()
    if not cfg:
        cfg = SystemConfig()
        db.add(cfg)
    # Update all configurable fields
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(cfg, field, value)
    await db.commit()
    await db.refresh(cfg)
    return cfg


@router.get("/tasks")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(10000, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    # Count total
    from sqlalchemy import func
    count_result = await db.execute(select(func.count()).select_from(ScanTask))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(ScanTask).order_by(ScanTask.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )
    tasks = result.scalars().all()
    items = [ScanTaskResponse(
        id=str(t.id), status=t.status, started_at=t.started_at,
        finished_at=t.finished_at, duration=t.duration,
        total_ips=t.total_ips, updated_ips=t.updated_ips,
        error_message=t.error_message, triggered_by=t.triggered_by,
        created_at=t.created_at
    ) for t in tasks]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


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


# ============ 入库网段管理 ============

@router.get("/subnets", response_model=List[ScanSubnetResponse])
async def list_subnets(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    """获取所有入库网段"""
    result = await db.execute(select(ScanSubnet).order_by(ScanSubnet.created_at.desc()))
    subnets = result.scalars().all()
    return [ScanSubnetResponse(
        id=str(s.id), cidr=s.cidr, description=s.description,
        is_active=s.is_active, created_at=s.created_at, updated_at=s.updated_at
    ) for s in subnets]


@router.post("/subnets", response_model=ScanSubnetResponse, status_code=201)
async def create_subnet(
    body: ScanSubnetCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    """添加入库网段"""
    # 检查是否已存在
    result = await db.execute(select(ScanSubnet).where(ScanSubnet.cidr == body.cidr))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该网段已存在")
    
    subnet = ScanSubnet(cidr=body.cidr, description=body.description)
    db.add(subnet)
    await db.commit()
    await db.refresh(subnet)
    
    return ScanSubnetResponse(
        id=str(subnet.id), cidr=subnet.cidr, description=subnet.description,
        is_active=subnet.is_active, created_at=subnet.created_at, updated_at=subnet.updated_at
    )


@router.patch("/subnets/{subnet_id}", response_model=ScanSubnetResponse)
async def update_subnet(
    subnet_id: str,
    body: ScanSubnetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    """更新入库网段"""
    result = await db.execute(select(ScanSubnet).where(ScanSubnet.id == subnet_id))
    subnet = result.scalar_one_or_none()
    if not subnet:
        raise HTTPException(status_code=404, detail="网段不存在")
    
    if body.description is not None:
        subnet.description = body.description
    if body.is_active is not None:
        subnet.is_active = body.is_active
    
    await db.commit()
    await db.refresh(subnet)
    
    return ScanSubnetResponse(
        id=str(subnet.id), cidr=subnet.cidr, description=subnet.description,
        is_active=subnet.is_active, created_at=subnet.created_at, updated_at=subnet.updated_at
    )


@router.delete("/subnets/{subnet_id}", status_code=204)
async def delete_subnet(
    subnet_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_role("admin"))
):
    """删除入库网段"""
    result = await db.execute(select(ScanSubnet).where(ScanSubnet.id == subnet_id))
    subnet = result.scalar_one_or_none()
    if not subnet:
        raise HTTPException(status_code=404, detail="网段不存在")
    
    await db.delete(subnet)
    await db.commit()
