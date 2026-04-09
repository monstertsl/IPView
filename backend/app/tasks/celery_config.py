from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery = Celery(
    "ipview",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.scan", "app.tasks.beat"]
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Scheduled tasks
celery.conf.beat_schedule = {
    # Daily log cleanup at 3 AM UTC
    "daily-log-cleanup": {
        "task": "app.tasks.beat.cleanup_old_logs",
        "schedule": crontab(hour=3, minute=0),
    },
    # Auto SNMP scan — hourly trigger, actual execution controlled by DB config
    "auto-snmp-scan": {
        "task": "app.tasks.beat.auto_scan",
        "schedule": crontab(minute=0),
    },
}
