from typing import NotRequired, TypedDict

from celery.schedules import crontab, schedule

from app.core.config import settings


class CeleryTaskSettings(TypedDict):
    task: str
    schedule: crontab | schedule
    args: NotRequired[tuple]


class CeleryConfig(TypedDict):
    task_name: CeleryTaskSettings


beat_schedule: dict[str, CeleryTaskSettings] = {
    "seed-users": {
        "task": "seed_fake_users",
        "schedule": schedule(run_every=10),  # Every 10 seconds
        "args": (settings.seeding_user_count,),
    }
}
