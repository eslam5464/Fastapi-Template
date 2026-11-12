from typing import NotRequired, TypedDict

from celery.schedules import crontab, schedule

# --- FEATURE[auth] START ---
from app.core.config import settings

# --- FEATURE[auth] END ---


class CeleryTaskSettings(TypedDict):
    task: str
    schedule: crontab | schedule
    args: NotRequired[tuple]


class CeleryConfig(TypedDict):
    task_name: CeleryTaskSettings


beat_schedule: dict[str, CeleryTaskSettings] = {}

# --- FEATURE[auth] START ---
SEED_USERS_SCHEDULE: CeleryTaskSettings = {
    "task": "seed_fake_users",
    "schedule": schedule(run_every=10),  # Every 10 seconds
    "args": (settings.seeding_user_count,),
}
if settings.enable_data_seeding:
    beat_schedule["seed-users"] = SEED_USERS_SCHEDULE
# --- FEATURE[auth] END ---
