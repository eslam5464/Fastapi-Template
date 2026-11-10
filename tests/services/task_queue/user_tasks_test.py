"""Tests for the user seeding task and its beat schedule entry."""

from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.models import User
from app.services.task_queue import celery_app
from app.services.task_queue.celery_config import SEED_USERS_SCHEDULE, beat_schedule
from app.services.task_queue.tasks.user_tasks import seed_fake_users_task


class TestSeedUsersSchedule:
    def test_schedule_entry_follows_data_seeding_setting(self):
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
