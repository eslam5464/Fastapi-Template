# Features

Full list of what's built into this template: what each integration does, which module implements it, which optional extra (if any) it needs, and how to configure it. `README.md` only lists the headline items — this is the complete reference.

## Core

- **FastAPI** — async web framework. Versioned routers mounted at `/v1` and `/v2` (`app/api/v1/`, `app/api/v2/`), each with its own interactive docs (`/v1/docs`, `/v2/docs`).
- **Async PostgreSQL** — SQLAlchemy 2.0 async engine (`asyncpg`) for the app, plus a sync engine (`psycopg`) for Celery. Both configured in `app/core/db.py` from `settings.db_url` / `db_url_sync`.
- **Database migrations** — Alembic (`app/alembic/`). Run via `./scripts/alembic.sh` / `.bat` or `alembic upgrade head` directly.
- **Clean/layered architecture** — repository pattern (`app/repos/`) + dependency injection, with module boundaries enforced by `tach` (see `tach.toml`): `core` → `models`/`schemas` → `repos` → `services` → `api`/`middleware`.
- **Structured logging** — Loguru-based (`app/core/logger.py`), with centralized log aggregation support.
- **Automatic API documentation** — Swagger UI and ReDoc, generated per API version.

No optional extra required — always installed.

## Authentication

- **JWT-based auth** — access + refresh tokens, implemented in `app/services/auth_service.py`. Password hashing via Argon2 (`pwdlib`).
- **Token blacklisting** — secure logout support, backed by Redis (`app/services/cache/token_blacklist.py`).
- **Protected routes** — dependency-injected via `app/api/v1/deps/` / `app/api/v2/deps/`.

No optional extra required beyond `cache` (for token blacklisting — see below).

## Security middleware

All in `app/middleware/`:

- **CSRF protection** (`csrf.py`)
- **Security headers** (`security_headers.py`)
- **Rate limiting** (`rate_limit.py`) — sliding-window algorithm with microsecond precision, Redis-backed.
- **Request logging** (`logging.py`)

Rate limiting and CSRF token storage require the `cache` extra (Redis).

## Caching

- **Redis caching** — shared connection pooling, decorator-based caching helpers (`app/services/cache/manager.py`, `decorators.py`).
- Install: `uv sync --extra cache`
- Configure: `REDIS_HOST`, `REDIS_PORT`, `REDIS_USER`, `REDIS_PASS` in `.env`.

## Background jobs / task queue

- **Celery** with Redis as the broker (`app/services/task_queue/`). Includes a sample scheduled task (`seed_fake_users`, runs every 10s when `ENABLE_DATA_SEEDING=true`).
- Install: `uv sync --extra task-queue`
- Start a worker: `./scripts/celery_worker.sh` (or `.bat`) — or directly: `celery -A app.services.task_queue worker --loglevel=info --pool=solo`
- Start the scheduler: `./scripts/celery_beat.sh` (or `.bat`) — or directly: `celery -A app.services.task_queue beat --loglevel=info`

## Cloud storage

- **BackBlaze B2** (`app/services/back_blaze_b2.py`) — B2 cloud storage client, schemas in `app/schemas/back_blaze_bucket.py`.
- **Google Cloud Storage** (`app/services/gcs.py`) — GCS bucket integration for file management, schemas in `app/schemas/google_bucket.py`.
- Install: `uv sync --extra cloud-service`

## Firebase

- **Firebase Admin** (`app/services/firebase.py`) — authentication and push notifications.
- **Firestore** (`app/services/firestore.py`) — Firestore database access.
- Credentials modeled by `FirebaseServiceAccount` in `app/core/credentials.py`.
- Install: `uv sync --extra cloud-service`

## Apple Pay

- **App Store Server API integration** (`app/services/payments/apple_pay.py`) — in-app purchase and subscription verification.
- Credentials modeled by `ApplePayStoreCredentials` in `app/core/credentials.py`.
- Install: `uv sync --extra apple-services`
- Configure: `APPLE_PAY_STORE_PRIVATE_KEY_PATH`, `APPLE_PAY_STORE_ROOT_CERTIFICATE_PATH`, plus key/issuer/bundle IDs in `.env`.

## Email

- **Brevo** and **Resend** provider adapters (`app/services/email/brevo.py`, `resend.py`), sharing a common interface (`app/services/email/base.py`).
- Install: `uv sync --extra email`
- Configure: `brevo_api_key`, `resend_api_key` in `.env`.

## Testing & quality tooling

- **pytest** with async support (`anyio`), coverage reporting (terminal + HTML), and custom markers (`unit`, `integration`, `slow`, `websocket`). ~90% coverage maintained across modules.
- **ruff** — linting and formatting.
- **mypy** — static typing, strict on `repos`/`models`/`services`.
- **bandit** — security static analysis.
- **detect-secrets** — secret-leak scanning.
- **tach** — module boundary enforcement (see `tach.toml`).
- **pre-commit** — runs all of the above locally before commit; `commitizen` additionally lints commit messages against Conventional Commits (see [Contributing](guides/contributing.md)).
- **CI** — GitHub Actions runs the same lint/type/security suite plus the full test suite against real Postgres + Redis containers, with a coverage badge/comment posted per PR (green ≥90%, orange ≥70%).

No optional extra required — all dev/test tooling is in `dependency-groups.dev`/`.test`.

## Environment management

Multi-environment configuration via `pydantic-settings` (`app/core/config.py`), reading from `.env`: `local`, `dev`, `stg` (staging), `prd` (production). See `.env.example` for the full variable list.
