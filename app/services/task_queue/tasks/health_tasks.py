from app.services.task_queue import celery_app


@celery_app.task(name="ping")
def ping_task() -> str:
    """Return "pong": a quick check that a worker is consuming the queue."""
    return "pong"
