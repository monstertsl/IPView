"""Helper to write SystemLog entries from both API handlers and Celery tasks."""
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.log.system_log_model import SystemLog


async def write_system_log(
    db: AsyncSession,
    *,
    action: str,
    target_type: str,
    target_id: str | None = None,
    detail: str | None = None,
    operator: str | None = None,
    ip_address: str | None = None,
) -> None:
    """Insert a system_log row.  Caller is responsible for committing the session."""
    entry = SystemLog(
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        operator=operator,
        ip_address=ip_address,
    )
    db.add(entry)
