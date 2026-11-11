# Background jobs (Celery)

`app/services/task_queue/` holds the [Celery](https://docs.celeryq.dev/) app
(`celery_app` in `__init__.py`), its beat schedule (`celery_config.py`) and the tasks
(`tasks/`). Tasks use the synchronous SQLAlchemy engine and `session_factory` from
`app/core/db_sync.py` (driver `psycopg`), because Celery workers are not async.

The integration is included when the project is generated with
`--data services=custom --data include_celery=true` (or by answering "yes" to the Celery
question). It adds `celery[redis]` and `psycopg` to the dependencies, the Celery
settings, the worker/beat scripts in `scripts/`, and Redis as the broker and result
backend.

<!-- --- FEATURE[auth] START --- -->
With authentication, it also has a sample task that seeds fake users: it adds `faker` to
the dependencies and the `ENABLE_DATA_SEEDING` / `SEEDING_USER_COUNT` settings.
<!-- --- FEATURE[auth] END --- -->

## Configuration

The broker and result backend default to the project's Redis (`REDIS_HOST`,
`REDIS_PORT`, `REDIS_PASS`) on databases 1 and 2. Override them, and the other Celery
settings, in `.env` if needed:

```env
# CELERY_BROKER_URL=redis://redis:6379/1
# CELERY_RESULT_BACKEND=redis://redis:6379/2
# CELERY_TIMEZONE=UTC
# CELERY_TASK_TIME_LIMIT=300
```

<!-- --- FEATURE[auth] START --- -->
The sample user seeding schedule:

```env
ENABLE_DATA_SEEDING=False      # turns the sample seed_fake_users schedule on
SEEDING_USER_COUNT=1
```
<!-- --- FEATURE[auth] END --- -->

## Running

```bash
# Worker (Linux/macOS, then Windows)
./scripts/celery_worker.sh
.\scripts\celery_worker.bat
# or directly
celery -A app.services.task_queue worker --loglevel=info --pool=solo

# Beat scheduler
./scripts/celery_beat.sh
.\scripts\celery_beat.bat
# or directly
celery -A app.services.task_queue beat --loglevel=info
```

## Tasks

- `ping()` (`tasks/health_tasks.py`) returns `"pong"`: a quick check that a worker is
  consuming the queue.
<!-- --- FEATURE[auth] START --- -->
- `seed_fake_users(count)` (`tasks/user_tasks.py`) inserts `count` fake users. Beat runs
  it every 10 seconds with `SEEDING_USER_COUNT` when `ENABLE_DATA_SEEDING=true`; it is
  meant for local development data, not production.
<!-- --- FEATURE[auth] END --- -->

Add tasks in `app/services/task_queue/tasks/` (they are auto-discovered) and schedule them
in `celery_config.py`:

```python
from app.core.db_sync import session_factory
from app.services.task_queue import celery_app


@celery_app.task(name="cleanup_expired_things")
def cleanup_expired_things() -> int:
    with session_factory() as session:
        ...
        session.commit()
    return 0
```

## Production

- Run workers and beat as their own processes or containers (beat exactly once)
- Keep task arguments JSON-serializable (the app only accepts JSON)
- Set `CELERY_TASK_TIME_LIMIT` to bound runaway tasks
<!-- --- FEATURE[auth] START --- -->
- Keep `ENABLE_DATA_SEEDING=false`
<!-- --- FEATURE[auth] END --- -->
