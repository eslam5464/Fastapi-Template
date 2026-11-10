"""Tests for the Celery app, its beat schedule and the user seeding task."""

from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.models import User
from app.services.task_queue import celery_app
from app.services.task_queue.celery_config import SEED_USERS_SCHEDULE, beat_schedule
from app.services.task_queue.tasks.user_tasks import seed_fake_users_task


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

    def test_beat_schedule_follows_data_seeding_setting(self):
        assert celery_app.conf.beat_schedule == beat_schedule
        assert ("seed-users" in beat_schedule) == settings.enable_data_seeding
        if settings.enable_data_seeding:
            assert beat_schedule["seed-users"] == SEED_USERS_SCHEDULE

    def test_scheduled_task_is_registered(self):
        assert SEED_USERS_SCHEDULE["task"] in celery_app.tasks
        assert SEED_USERS_SCHEDULE["args"] == (settings.seeding_user_count,)


class TestSeedFakeUsersTask:
    def test_inserts_the_requested_number_of_users(self):
        session = MagicMock()
        factory = MagicMock()
        factory.return_value.__enter__.return_value = session

        with patch("app.services.task_queue.tasks.user_tasks.session_factory", factory):
            with patch("app.services.task_queue.tasks.user_tasks.password_hash.hash", return_value="hashed"):
                result = seed_fake_users_task.apply(args=(3,)).get()

        assert result == 3
        session.execute.assert_called_once()
        session.commit.assert_called_once()
        statement = session.execute.call_args.args[0]
        assert statement.table.name == User.__tablename__
        params = statement.compile().params
        assert sum(1 for key in params if key.startswith("username")) == 3
