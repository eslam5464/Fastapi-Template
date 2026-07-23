# 🧩 Features & Integrations

Full reference for what's built into this template: what each integration does, which module implements it, which optional extra (if any) it needs, and how to configure it. [`README.md`](../README.md) only lists the headline items — this is the complete picture.

## 📋 Quick Reference

| Feature | Optional extra | Section |
|---|---|---|
| 🚀 Core (FastAPI, Postgres, Alembic, logging, docs) | — always installed | [Core](#-core) |
| 🔐 Authentication (JWT, Argon2, blacklisting) | `cache` for blacklisting | [Authentication](#-authentication) |
| 🔒 Security middleware (CSRF, headers, rate limiting) | `cache` for rate limiting | [Security middleware](#-security-middleware) |
| ⚡ Caching | `cache` | [Caching](#-caching) |
| ⚙️ Background jobs (Celery) | `task-queue` | [Background jobs](#-background-jobs--task-queue) |
| ☁️ Cloud storage (BackBlaze B2, GCS) | `cloud-service` | [Cloud storage](#-cloud-storage) |
| 🔥 Firebase (Auth, Firestore) | `cloud-service` | [Firebase](#-firebase) |
| 💳 Apple Pay | `apple-services` | [Apple Pay](#-apple-pay) |
| 📧 Email (Brevo, Resend) | `email` | [Email](#-email) |
| 🧪 Testing & quality tooling | dev/test groups | [Testing & quality tooling](#-testing--quality-tooling) |
| 🌍 Environment management | — always installed | [Environment management](#-environment-management) |

Install optional extras individually as needed:

```bash
uv sync --extra email
uv sync --extra cloud-service
uv sync --extra cache
uv sync --extra task-queue
uv sync --extra apple-services
```

---

## 🚀 Core

*Always installed — no extra required.*

- **FastAPI** — async web framework. Versioned routers mounted at `/v1` and `/v2` (`app/api/v1/`, `app/api/v2/`), each with its own interactive docs (`/v1/docs`, `/v2/docs`).
- **Async PostgreSQL** — SQLAlchemy 2.0 async engine (`asyncpg`) for the app, plus a sync engine (`psycopg`) for Celery. Both configured in `app/core/db.py` from `settings.db_url` / `db_url_sync`.
- **Database migrations** — Alembic (`app/alembic/`). Run via `./scripts/alembic.sh` / `.bat` or `alembic upgrade head` directly.
- **Clean/layered architecture** — repository pattern (`app/repos/`) + dependency injection, with module boundaries enforced by `tach` (see `tach.toml`): `core` → `models`/`schemas` → `repos` → `services` → `api`/`middleware`.
- **Structured logging** — Loguru-based (`app/core/logger.py`), with centralized log aggregation support.
- **Automatic API documentation** — Swagger UI and ReDoc, generated per API version.

## 🔐 Authentication

*Requires `cache` for token blacklisting.*

- **JWT-based auth** — access + refresh tokens, implemented in `app/services/auth_service.py`. Password hashing via Argon2 (`pwdlib`).
- **Token blacklisting** — secure logout support, backed by Redis (`app/services/cache/token_blacklist.py`).
- **Protected routes** — dependency-injected via `app/api/v1/deps/` / `app/api/v2/deps/`.

## 🔒 Security middleware

*Rate limiting and CSRF token storage require `cache`.*

All in `app/middleware/`:

- **CSRF protection** (`csrf.py`)
- **Security headers** (`security_headers.py`)
- **Rate limiting** (`rate_limit.py`) — sliding-window algorithm with microsecond precision, Redis-backed.
- **Request logging** (`logging.py`)

## ⚡ Caching

- **Module:** `app/services/cache/manager.py`, `decorators.py`
- **Redis caching** — shared connection pooling, decorator-based caching helpers.
- **Install:** `uv sync --extra cache`
- **Configure:** `REDIS_HOST`, `REDIS_PORT`, `REDIS_USER`, `REDIS_PASS` in `.env`

## ⚙️ Background jobs / task queue

- **Module:** `app/services/task_queue/`
- **Celery** with Redis as the broker. Includes a sample scheduled task (`seed_fake_users`, runs every 10s when `ENABLE_DATA_SEEDING=true`).
- **Install:** `uv sync --extra task-queue`
- **Start a worker:** `./scripts/celery_worker.sh` (or `.bat`) — or directly: `celery -A app.services.task_queue worker --loglevel=info --pool=solo`
- **Start the scheduler:** `./scripts/celery_beat.sh` (or `.bat`) — or directly: `celery -A app.services.task_queue beat --loglevel=info`

## ☁️ Cloud storage

- **BackBlaze B2** — `app/services/back_blaze_b2.py`, schemas in `app/schemas/back_blaze_bucket.py`.
- **Google Cloud Storage** — `app/services/gcs.py`, schemas in `app/schemas/google_bucket.py`.
- **Install:** `uv sync --extra cloud-service`

## 🔥 Firebase

- **Firebase Admin** — `app/services/firebase.py` — authentication and push notifications.
- **Firestore** — `app/services/firestore.py` — Firestore database access.
- **Credentials:** modeled by `FirebaseServiceAccount` in `app/core/credentials.py`.
- **Install:** `uv sync --extra cloud-service`

## 💳 Apple Pay

- **Module:** `app/services/payments/apple_pay.py`
- **App Store Server API integration** — in-app purchase and subscription verification.
- **Credentials:** modeled by `ApplePayStoreCredentials` in `app/core/credentials.py`.
- **Install:** `uv sync --extra apple-services`
- **Configure:** `APPLE_PAY_STORE_PRIVATE_KEY_PATH`, `APPLE_PAY_STORE_ROOT_CERTIFICATE_PATH`, plus key/issuer/bundle IDs in `.env`
- **Note:** this is the one feature generated projects can opt out of entirely — see [Using This as a Template](../README.md#-using-this-as-a-template) in the main README.

## 📧 Email

- **Module:** `app/services/email/brevo.py`, `resend.py`, sharing a common interface (`base.py`)
- **Brevo** and **Resend** provider adapters.
- **Install:** `uv sync --extra email`
- **Configure:** `brevo_api_key`, `resend_api_key` in `.env`

## 🧪 Testing & quality tooling

*Always installed via `dependency-groups.dev` / `.test` — no extra required.*

- **pytest** with async support (`anyio`), coverage reporting (terminal + HTML), and custom markers (`unit`, `integration`, `slow`, `websocket`). ~90% coverage maintained across modules.
- **ruff** — linting and formatting.
- **mypy** — static typing, strict on `repos`/`models`/`services`.
- **bandit** — security static analysis.
- **detect-secrets** — secret-leak scanning.
- **tach** — module boundary enforcement (see `tach.toml`).
- **pre-commit** — runs all of the above locally before commit; `commitizen` additionally lints commit messages against Conventional Commits (see [Contributing](guides/contributing.md)).
- **CI** — GitHub Actions runs the same lint/type/security suite plus the full test suite against real Postgres + Redis containers, with a coverage badge/comment posted per PR (green ≥90%, orange ≥70%).

## 🌍 Environment management

*Always installed — no extra required.*

Multi-environment configuration via `pydantic-settings` (`app/core/config.py`), reading from `.env`: `local`, `dev`, `stg` (staging), `prd` (production). See `.env.example` for the full variable list.
