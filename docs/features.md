# 🧩 Features & Integrations

Full reference for what's built into this project: what each feature does, which module implements it, and how to configure it. [`README.md`](../README.md) only lists the headline items — this is the complete picture.

## 📋 Quick Reference

- 🚀 [Core](#-core) — FastAPI, Postgres, Alembic, logging, docs (always included)
- 🔐 [Authentication](#-authentication) — JWT, Argon2
- 🔒 [Security middleware](#-security-middleware) — security headers and the other request middleware
<!-- --- FEATURE[redis_cache] START --- -->
- ⚡ [Caching](#-caching) — Redis cache
<!-- --- FEATURE[redis_cache] END --- -->
<!-- --- FEATURE[celery] START --- -->
- ⚙️ [Background jobs](#-background-jobs--task-queue) — Celery
<!-- --- FEATURE[celery] END --- -->
<!-- --- FEATURE[gcs] START --- -->
- ☁️ [Cloud storage](#-cloud-storage) — Google Cloud Storage
<!-- --- FEATURE[gcs] END --- -->
<!-- --- FEATURE[backblaze] START --- -->
- ☁️ [Cloud storage](#-cloud-storage) — BackBlaze B2
<!-- --- FEATURE[backblaze] END --- -->
<!-- --- FEATURE[firebase] START --- -->
- 🔥 [Firebase](#-firebase) — Authentication, users, push notifications
<!-- --- FEATURE[firestore] START --- -->
- 🔥 [Firestore](#-firebase) — document database
<!-- --- FEATURE[firestore] END --- -->
<!-- --- FEATURE[firebase] END --- -->
<!-- --- FEATURE[apple_pay] START --- -->
- 💳 [Apple Pay](#-apple-pay) — App Store Server API
<!-- --- FEATURE[apple_pay] END --- -->
<!-- --- FEATURE[resend] START --- -->
- 📧 [Email](#-email) — Resend
<!-- --- FEATURE[resend] END --- -->
<!-- --- FEATURE[brevo] START --- -->
- 📧 [Email](#-email) — Brevo
<!-- --- FEATURE[brevo] END --- -->
- 🧪 [Testing & quality tooling](#-testing--quality-tooling)
- 🌍 [Environment management](#-environment-management)

Optional services are chosen when the project is generated (Copier's `services=custom` questions); a chosen service's packages are regular dependencies, so `uv sync` installs everything the project uses.

---

## 🚀 Core

*Always included.*

- **FastAPI** — async web framework. Each API version is its own mounted app with its own interactive docs: `app/api/v1/` at `/v1` (`/v1/docs`).
<!-- --- FEATURE[api_v2] START --- -->
- **Second API version** — an empty scaffold in `app/api/v2/`, mounted at `/v2` with its own docs (`/v2/docs`).
<!-- --- FEATURE[api_v2] END --- -->
- **Async PostgreSQL** — SQLAlchemy 2.0 async engine (`asyncpg`) for the app, configured in `app/core/db.py` from `settings.db_url`.
<!-- --- FEATURE[celery] START --- -->
- **Sync engine for Celery** — `psycopg` engine and `session_factory` in `app/core/db_sync.py`, from `settings.db_url_sync`.
<!-- --- FEATURE[celery] END --- -->
- **Database migrations** — Alembic (`app/alembic/`). Run via `./scripts/alembic.sh` / `.bat` or `alembic upgrade head` directly.
- **Clean/layered architecture** — repository pattern (`app/repos/`) + dependency injection, with module boundaries enforced by `tach` (see `tach.toml`): `core` → `models`/`schemas` → `repos` → `services` → `api`/`middleware`.
- **Structured logging** — Loguru-based (`app/core/logger.py`): console and rotating file output, request and process IDs.
<!-- --- FEATURE[openobserve] START --- -->
- **Log shipping** — non-blocking, batched shipping to OpenObserve (`app/core/openobserve.py`). Guide: [integrations/openobserve.md](integrations/openobserve.md).
<!-- --- FEATURE[openobserve] END --- -->
- **Automatic API documentation** — Swagger UI and ReDoc, generated per API version.

## 🔐 Authentication

- **JWT-based auth** — access + refresh tokens, implemented in `app/services/auth_service.py`. Password hashing via Argon2 (`pwdlib`).
<!-- --- FEATURE[redis_token_blacklist] START --- -->
- **Token blacklisting** — logout revokes the token, backed by Redis (`app/services/cache/token_blacklist.py`). Guide: [integrations/token-revocation.md](integrations/token-revocation.md).
<!-- --- FEATURE[redis_token_blacklist] END --- -->
<!-- --- FEATURE[!redis_token_blacklist] START --- -->
- **Logout** — logout returns `revoked: false` and the access token stays valid until it expires (no token blacklist).
<!-- --- FEATURE[!redis_token_blacklist] END --- -->
- **Protected routes** — dependency-injected via `app/api/v1/deps/`.

## 🔒 Security middleware

All in `app/middleware/`:

<!-- --- FEATURE[csrf] START --- -->
- **CSRF protection** (`csrf.py`) — double-submit cookie check (`X-CSRF-Token` header against the `csrf_token` cookie) on state-changing requests.
<!-- --- FEATURE[csrf] END --- -->
<!-- --- FEATURE[!csrf] START --- -->
- **No cross-site request forgery check** — this project was generated without that middleware. Add one before you authenticate browser clients with cookies.
<!-- --- FEATURE[!csrf] END --- -->
- **Security headers** (`security_headers.py`)
<!-- --- FEATURE[redis_rate_limit] START --- -->
- **Rate limiting** (`rate_limit.py`) — sliding-window algorithm with microsecond precision, Redis-backed. Guide: [integrations/rate-limiting.md](integrations/rate-limiting.md).
<!-- --- FEATURE[redis_rate_limit] END --- -->
- **Request logging** (`logging.py`)

<!-- --- FEATURE[redis_cache] START --- -->
## ⚡ Caching

- **Module:** `app/services/cache/manager.py` (`cache_manager`), `decorators.py` (`@cache_result`). Guide: [integrations/caching.md](integrations/caching.md).
- **Redis caching** — shared connection pooling, decorator-based caching helpers.
- **Included** when the project is generated with `include_redis_cache`; Redis (`redis`, the `REDIS_*` settings, the compose service) comes with it.
<!-- --- FEATURE[redis_cache] END --- -->

<!-- --- FEATURE[celery] START --- -->
## ⚙️ Background jobs / task queue

- **Module:** `app/services/task_queue/`. Guide: [integrations/celery.md](integrations/celery.md).
- **Celery** with Redis as the broker. Includes a sample scheduled task (`seed_fake_users`, runs every 10s when `ENABLE_DATA_SEEDING=true`).
- **Included** when the project is generated with `include_celery`; `celery[redis]` and `psycopg` are then regular dependencies.
- **Start a worker:** `./scripts/celery_worker.sh` (or `.bat`) — or directly: `celery -A app.services.task_queue worker --loglevel=info --pool=solo`
- **Start the scheduler:** `./scripts/celery_beat.sh` (or `.bat`) — or directly: `celery -A app.services.task_queue beat --loglevel=info`
<!-- --- FEATURE[celery] END --- -->

<!-- --- FEATURE[backblaze|gcs] START --- -->
## ☁️ Cloud storage

<!-- --- FEATURE[backblaze] START --- -->
- **BackBlaze B2** — `app/services/back_blaze_b2.py`, schemas in `app/schemas/back_blaze_bucket.py`. Guide: [integrations/backblaze.md](integrations/backblaze.md).
<!-- --- FEATURE[backblaze] END --- -->
<!-- --- FEATURE[gcs] START --- -->
- **Google Cloud Storage** — `app/services/gcs.py`, schemas in `app/schemas/google_bucket.py`. Guide: [integrations/gcs.md](integrations/gcs.md).
<!-- --- FEATURE[gcs] END --- -->
- **Included** because they were chosen when the project was generated; their SDKs are then regular dependencies.
<!-- --- FEATURE[backblaze|gcs] END --- -->

<!-- --- FEATURE[firebase] START --- -->
## 🔥 Firebase

- **Firebase Admin** — `app/services/firebase.py` — authentication and push notifications. Guide: [integrations/firebase.md](integrations/firebase.md).
<!-- --- FEATURE[firestore] START --- -->
- **Firestore** — `app/services/firestore.py` — Firestore database access. Guide: [integrations/firestore.md](integrations/firestore.md).
<!-- --- FEATURE[firestore] END --- -->
- **Credentials:** modeled by `FirebaseServiceAccount` in `app/core/credentials/firebase.py`, from the `FIREBASE_*` settings.
- **Included** when the project is generated with `include_firebase`; `firebase-admin` is then a regular dependency.
<!-- --- FEATURE[firebase] END --- -->

<!-- --- FEATURE[apple_pay] START --- -->
## 💳 Apple Pay

- **Module:** `app/services/payments/apple_pay.py`
- **App Store Server API integration** — in-app purchase and subscription verification.
- **Credentials:** modeled by `ApplePayStoreCredentials` in `app/core/credentials/apple_pay.py`.
- **Included** when the project is generated with `include_apple_pay`; `app-store-server-library` is then a regular dependency. Guide: [integrations/apple-pay.md](integrations/apple-pay.md).
- **Configure:** `APPLE_PAY_STORE_PRIVATE_KEY_PATH`, `APPLE_PAY_STORE_ROOT_CERTIFICATE_PATH`, plus key/issuer/bundle IDs in `.env`

<!-- --- FEATURE[apple_pay] END --- -->

<!-- --- FEATURE[resend|brevo] START --- -->
## 📧 Email

- **Module:** `app/services/email/`, providers sharing a common interface (`base.py`). Guide: [integrations/email.md](integrations/email.md).
<!-- --- FEATURE[brevo] START --- -->
- **Brevo:** `app/services/email/brevo.py`, configured with `BREVO_API_KEY`.
<!-- --- FEATURE[brevo] END --- -->
<!-- --- FEATURE[resend] START --- -->
- **Resend:** `app/services/email/resend.py`, configured with `RESEND_API_KEY`.
<!-- --- FEATURE[resend] END --- -->
- **Included** when at least one email provider was chosen at generation; each chosen provider's SDK is then a regular dependency.
<!-- --- FEATURE[resend|brevo] END --- -->

## 🧪 Testing & quality tooling

*Always installed via `dependency-groups.dev` / `.test` — no extra required.*

- **pytest** with async support (`anyio`), coverage reporting (terminal + HTML), and custom markers (`unit`, `integration`, `slow`, `websocket`). ~90% coverage maintained across modules.
- **ruff** — linting and formatting.
- **mypy** — static typing, strict on `repos`/`models`/`services`.
- **bandit** — security static analysis.
- **detect-secrets** — secret-leak scanning.
- **tach** — module boundary enforcement (see `tach.toml`).
- **pre-commit** — runs all of the above locally before commit; `commitizen` additionally lints commit messages against Conventional Commits (see [Contributing](guides/contributing.md)).
- **CI** — GitHub Actions runs the same lint/type/security suite plus the full test suite against real service containers (Postgres, plus any other service the project uses), with a coverage badge/comment posted per PR (green ≥90%, orange ≥70%).

## 🌍 Environment management

*Always included.*

Multi-environment configuration via `pydantic-settings` (`app/core/config.py`), reading from `.env`: `local`, `dev`, `stg` (staging), `prd` (production). See `.env.example` for the full variable list.
