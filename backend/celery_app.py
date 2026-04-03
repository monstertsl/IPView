# Root Celery entrypoint — imports config from app.tasks.celery_config
from app.tasks.celery_config import celery

__all__ = ["celery"]
