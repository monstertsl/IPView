from datetime import datetime, timedelta
from sqlalchemy import select, delete, or_, and_, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.tasks.celery_config import celery
from app.core.config import settings
from app.models.log.log_model import LoginLog
from app.models.scan.scan_model import ScanTask, TriggerType
from app.models.system.system_model import SystemConfig
from app.models.user.user_model import User, UserRole


async def _cleanup_old_logs(db: AsyncSession) -> dict:
    """Delete login/scan history older than the configured retention windows."""
    cfg = (await db.execute(select(SystemConfig).limit(1))).scalar_one_or_none()
    login_retention = cfg.log_retention_days_login if cfg else settings.LOG_RETENTION_DAYS_LOGIN
    scan_retention = cfg.log_retention_days_scan if cfg else settings.LOG_RETENTION_DAYS_SCAN

    login_cutoff = datetime.utcnow() - timedelta(days=login_retention)
    scan_cutoff = datetime.utcnow() - timedelta(days=scan_retention)

    r1 = await db.execute(delete(LoginLog).where(LoginLog.created_at < login_cutoff))
    r2 = await db.execute(delete(ScanTask).where(ScanTask.created_at < scan_cutoff))
    await db.commit()
    return {"login_deleted": r1.rowcount or 0, "scan_deleted": r2.rowcount or 0}


async def _deactivate_inactive_users(db: AsyncSession) -> dict:
    """Disable non-admin users idle longer than ``SystemConfig.inactive_days_limit`` days.

    - Admin accounts are never auto-disabled.
    - A never-logged-in account is judged by ``created_at`` so brand-new users aren't locked out.
    - Already-disabled users are skipped.
    - Disabled users have their Redis status cache invalidated so any outstanding JWT is rejected
      on the next request.
    """
    from app.core.rate_limit import invalidate_user_status  # avoid import cycle at module load

    cfg = (await db.execute(select(SystemConfig).limit(1))).scalar_one_or_none()
    limit_days = cfg.inactive_days_limit if cfg else settings.INACTIVE_DAYS_LIMIT
    if not limit_days or limit_days <= 0:
        return {"skipped": "inactive_days_limit not configured", "disabled": 0}

    cutoff = datetime.utcnow() - timedelta(days=limit_days)

    stmt = select(User.id).where(
        and_(
            User.is_active.is_(True),
            User.role != UserRole.admin,
            or_(
                and_(User.last_login_at.is_(None), User.created_at < cutoff),
                User.last_login_at < cutoff,
            ),
        )
    )
    ids = [row[0] for row in (await db.execute(stmt)).all()]
    if not ids:
        return {"disabled": 0, "limit_days": limit_days}

    await db.execute(update(User).where(User.id.in_(ids)).values(is_active=False))
    await db.commit()

    for uid in ids:
        try:
            await invalidate_user_status(str(uid))
        except Exception:
            pass

    return {"disabled": len(ids), "limit_days": limit_days}


@celery.task
def daily_maintenance():
    """One daily maintenance pass: clean old logs, then deactivate long-inactive users.

    Each step is independent — a failure in one does not prevent the other from running.
    """

    async def _run():
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        result = {"log_cleanup": None, "user_deactivation": None}

        async with session_maker() as db:
            try:
                result["log_cleanup"] = await _cleanup_old_logs(db)
            except Exception as e:
                await db.rollback()
                result["log_cleanup"] = {"error": str(e)}

            try:
                result["user_deactivation"] = await _deactivate_inactive_users(db)
            except Exception as e:
                await db.rollback()
                result["user_deactivation"] = {"error": str(e)}

        return result

    import asyncio
    return asyncio.run(_run())


@celery.task
def auto_scan():
    """Periodic SNMP scan triggered by Celery Beat (every hour).
    Actual execution is controlled by scan_interval and scan_time in SystemConfig."""
    from app.tasks.scan import run_scan_task
    from app.models.switch.switch_model import Switch

    async def _check_and_enqueue():
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with session_maker() as db:
            # Load config
            cfg_result = await db.execute(select(SystemConfig).limit(1))
            cfg = cfg_result.scalar_one_or_none()

            scan_interval = cfg.scan_interval if cfg else "every_day"
            scan_time = cfg.scan_time if cfg else "00:00"

            # Check if current time matches the schedule
            now = datetime.utcnow()
            current_hour = now.hour

            # Parse configured scan time
            try:
                target_hour = int(scan_time.split(":")[0])
            except (ValueError, IndexError):
                target_hour = 0

            should_run = False
            if scan_interval == "every_1h":
                should_run = True
            elif scan_interval == "every_6h":
                should_run = (current_hour % 6 == target_hour % 6)
            elif scan_interval == "every_12h":
                should_run = (current_hour % 12 == target_hour % 12)
            elif scan_interval == "every_day":
                should_run = (current_hour == target_hour)
            else:
                should_run = (current_hour == target_hour)

            if not should_run:
                return {"skipped": f"not scheduled (interval={scan_interval}, time={scan_time}, current_hour={current_hour})"}

            # Only run if there are active switches
            result = await db.execute(select(Switch).where(Switch.is_active == True))
            switches = result.scalars().all()
            if not switches:
                return {"skipped": "no active switches"}

            task = ScanTask(triggered_by=TriggerType.SYSTEM)
            db.add(task)
            await db.commit()
            await db.refresh(task)
            task_id = str(task.id)

        run_scan_task.delay(task_id)
        return {"task_id": task_id}

    import asyncio
    return asyncio.run(_check_and_enqueue())
