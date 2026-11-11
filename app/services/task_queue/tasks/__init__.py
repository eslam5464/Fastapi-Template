from app.services.task_queue.tasks import health_tasks

# --- FEATURE[auth] START ---
from app.services.task_queue.tasks import user_tasks

# --- FEATURE[auth] END ---

__all__ = [
    "health_tasks",
    # --- FEATURE[auth] START ---
    "user_tasks",
    # --- FEATURE[auth] END ---
]
