from datetime import datetime, timezone, timedelta
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.tasks.celery_config import celery
from app.core.config import settings
from app.core.database import async_session_maker
from app.models.log.log_model import LoginLog
from app.models.scan.scan_model import ScanLog
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

            login_cutoff = datetime.now(timezone.utc) - timedelta(days=login_retention)
            scan_cutoff = datetime.now(timezone.utc) - timedelta(days=scan_retention)

            r1 = await db.execute(delete(LoginLog).where(LoginLog.created_at < login_cutoff))
            r2 = await db.execute(delete(ScanLog).where(ScanLog.created_at < scan_cutoff))
            await db.commit()
            return {"login_deleted": r1.rowcount, "scan_deleted": r2.rowcount}

    import asyncio
    return asyncio.run(_cleanup())
