from datetime import datetime, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import uuid

from app.tasks.celery_config import celery
from app.core.config import settings
from app.models.log.log_model import LoginLog
from app.models.scan.scan_model import ScanLog, ScanTask, TriggerType
from app.models.system.system_model import SystemConfig


@celery.task
def cleanup_old_logs():
    """Daily cleanup — removes login/scan logs older than configured retention period."""
    async def _cleanup():
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with session_maker() as db:
            result = await db.execute(select(SystemConfig).limit(1))
            cfg = result.scalar_one_or_none()
            login_retention = cfg.log_retention_days_login if cfg else 90
            scan_retention = cfg.log_retention_days_scan if cfg else 30

            login_cutoff = datetime.utcnow() - timedelta(days=login_retention)
            scan_cutoff = datetime.utcnow() - timedelta(days=scan_retention)

            r1 = await db.execute(delete(LoginLog).where(LoginLog.created_at < login_cutoff))
            r2 = await db.execute(delete(ScanLog).where(ScanLog.created_at < scan_cutoff))
            await db.commit()
            return {"login_deleted": r1.rowcount, "scan_deleted": r2.rowcount}

    import asyncio
    return asyncio.run(_cleanup())


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
