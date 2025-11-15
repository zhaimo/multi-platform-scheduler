"""Celery application configuration"""

from celery import Celery
from src.config import settings

celery_app = Celery(
    "video_scheduler",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    task_soft_time_limit=3300,  # 55 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Celery beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "check-scheduled-posts": {
        "task": "src.tasks.check_scheduled_posts",
        "schedule": 60.0,  # Every minute
    },
    "sync-analytics": {
        "task": "src.tasks.sync_analytics",
        "schedule": 21600.0,  # Every 6 hours
    },
    "refresh-expiring-tokens": {
        "task": "src.tasks.refresh_expiring_tokens",
        "schedule": 3600.0,  # Every hour
    },
}
