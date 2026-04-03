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

# Daily log cleanup at 3 AM
celery.conf.beat_schedule = {
    "daily-log-cleanup": {
        "task": "app.tasks.beat.cleanup_old_logs",
        "schedule": crontab(hour=3, minute=0),
    },
}
