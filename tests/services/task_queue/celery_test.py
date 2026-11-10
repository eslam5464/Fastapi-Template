"""Tests for the Celery app and its configuration."""

from app.core.config import settings
from app.services.task_queue import celery_app
from app.services.task_queue.celery_config import beat_schedule


class TestCeleryApp:
    def test_broker_and_backend_come_from_settings(self):
        assert celery_app.conf.broker_url == settings.celery_broker.human_repr()
        assert celery_app.conf.result_backend == settings.celery_backend.human_repr()

    def test_default_urls_use_the_redis_databases(self):
        if settings.celery_broker_url is None:
            assert settings.celery_broker.path == f"/{settings.celery_broker_db}"
        if settings.celery_result_backend is None:
            assert settings.celery_backend.path == f"/{settings.celery_result_db}"

    def test_json_only_serialization(self):
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"
        assert celery_app.conf.accept_content == ["json"]

    def test_uses_the_configured_beat_schedule(self):
        assert celery_app.conf.beat_schedule == beat_schedule
