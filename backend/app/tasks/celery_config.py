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
    # Daily maintenance — log cleanup + auto-deactivate long-inactive users.
    # UTC 19:00 == Asia/Shanghai 03:00.
    "daily-maintenance": {
        "task": "app.tasks.beat.daily_maintenance",
        "schedule": crontab(hour=19, minute=0),
    },
    # Auto SNMP scan — hourly trigger, actual execution controlled by DB config
    "auto-snmp-scan": {
        "task": "app.tasks.beat.auto_scan",
        "schedule": crontab(minute=0),
    },
}
