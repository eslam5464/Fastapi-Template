from zoneinfo import ZoneInfo
from celery import Celery
from app.core.config import settings
from app.services.task_queue.celery_config import beat_schedule

celery_app = Celery(settings.app_name)

celery_app.conf.update(
    broker_url=settings.celery_broker.human_repr(),
    result_backend=settings.celery_backend.human_repr(),
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone=ZoneInfo(settings.celery_timezone),
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.celery_task_time_limit,
    worker_prefetch_multiplier=4,
    beat_schedule=beat_schedule if settings.enable_data_seeding else {},
)

celery_app.autodiscover_tasks(["app.services.task_queue.tasks"])


__all__ = ["celery_app"]
