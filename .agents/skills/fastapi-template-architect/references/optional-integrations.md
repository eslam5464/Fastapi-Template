# Optional Integrations

Source: `pyproject.toml` optional-dependency extras, `.env.example`, `docs/features.md`,
and the relevant `app/services/*` modules. None of these modules are snapshotted in
`../assets/` (they're feature-specific, not architecturally load-bearing the way the
base classes/middleware are) — **read the actual file in the target repo before
modifying one**; what's below is a map of what exists and how to reason about it, not a
substitute for the real source.

## The rule that governs this whole file

**None of the five integrations below are Copier generation-time toggles** — only
`include_apple_pay` is (see
[copier-template-mechanics.md](copier-template-mechanics.md)). Their code ships in every
generated project regardless. "Enabling" one of these for a project means: install its
`uv sync --extra <name>`, and fill in its `.env` config block. Don't present installing
an extra as equivalent to "generating the project with/without" that feature.

| Integration | Extra name | Key modules | Default behavior with no config |
|---|---|---|---|
| Email | `email` | `app/services/email/{base,resend,brevo}.py` | Not usable until an API key is set; no silent fallback |
| Cache (Redis) | `cache` | `app/services/cache/{base,manager,decorators,rate_limiter,token_blacklist}.py` | Fails open / no-op in `LOCAL` |
| Cloud storage | `cloud-service` | `app/services/{gcs,back_blaze_b2,firebase,firestore}.py` | Not usable until credentials are set |
| Task queue | `task-queue` | `app/services/task_queue/{celery_config.py, tasks/user_tasks.py}` | Inert unless a worker/beat process is actually started |
| Apple Pay | `apple-services` | `app/services/payments/apple_pay.py` | **Removable at generation time** — the one real toggle |

## Email (`email` extra)

`app/services/email/base.py` defines `BaseEmailService(ABC)` with an abstract `send()`
and a concrete `send_welcome()` helper that renders `static/welcome.html` via a naive
`{{key}}` string-replace (not a real templating engine — don't assume Jinja syntax works
in that HTML file). Two provider adapters, chosen by which API key is configured:
`resend.py` (wraps the sync `resend` SDK via `asyncio.to_thread`, since the SDK itself is
sync) and `brevo.py`. This is the one service in this repo that genuinely uses the
**abstract-base-with-multiple-implementations** pattern from
[schema-and-service-patterns.md](schema-and-service-patterns.md) — appropriate here
specifically because there are two real interchangeable providers. Config: `.env.example`
has `resend_api_key` / `brevo_api_key` — note these are **lowercase**, inconsistent with
the rest of the file's `UPPER_SNAKE_CASE` convention; that's a known quirk, not something
to "fix" silently as a side effect of an unrelated change.

## Cache / rate limiting / token blacklist (`cache` extra, Redis-backed)

`app/services/cache/manager.py`'s `CacheManager` is a pickle-serialized generic
key-value cache (`get/set/delete/delete_pattern/exists`) — pickle is used deliberately
here with a `# nosec` justification comment, under a trusted-infrastructure threat model
(don't assume this is safe if the cache ever becomes reachable by untrusted input).
`app/services/cache/rate_limiter.py` and `token_blacklist.py` are the concrete services
behind [auth-and-security.md](auth-and-security.md)'s rate limiting and token revocation.
All of them inherit fail-open behavior from `BaseRedisClient` — in the `LOCAL`
environment, `redis_client` returns `None` deliberately (Redis isn't assumed to be
running locally), so cache/rate-limit/blacklist operations become no-ops rather than
connection errors. `cache_manager`, `rate_limiter`, and `token_blacklist` are module-level
singletons, health-checked in `main.py`'s lifespan (see
[observability-and-performance.md](observability-and-performance.md)) and explicitly
closed on shutdown.

## Cloud storage & Firebase (`cloud-service` extra)

- `app/services/gcs.py` — Google Cloud Storage via `gcloud-aio-storage`, schema in
  `app/schemas/google_bucket.py`.
- `app/services/back_blaze_b2.py` — Backblaze B2 SDK, schema in
  `app/schemas/back_blaze_bucket.py`.
- `app/services/firebase.py` (Admin SDK auth) and `firestore.py` (Firestore DB) —
  credentials modeled by `FirebaseServiceAccount` in `app/core/credentials.py`, which
  supports either a raw key string or a file-path-based key and auto-escapes `\n` →
  `\\n` for a PEM key embedded directly in an env var.
- Each has its own exception module under `app/core/exceptions/` (`gcs_exceptions.py`,
  `back_blaze_exceptions.py`, `firebase_exceptions.py`) — note these live in `app/core/`
  rather than `app/services/exceptions/`, a documented deviation from the strict-profile
  domain-exception placement (same category of deviation as the `AppException`
  compatibility shim — see [layering-and-flow.md](layering-and-flow.md)).

## Task queue / background jobs (`task-queue` extra, Celery + Redis)

`app/services/task_queue/celery_config.py` defines a `beat_schedule` dict typed with a
`CeleryTaskSettings` `TypedDict`. The one sample scheduled task,
`seed_fake_users_task` (`app/services/task_queue/tasks/user_tasks.py`), runs every 10
seconds when `ENABLE_DATA_SEEDING=true`, using the **sync** session factory
(`session_factory` from `app/core/db.py` — Celery workers are sync, not async) to bulk
insert Faker-generated users. Celery broker/backend URLs are computed from separate
Redis DB indices (1 and 2) via `settings.celery_broker`/`celery_backend`. Run with:

```bash
celery -A app.services.task_queue worker --loglevel=info --pool=solo   # Windows-safe
celery -A app.services.task_queue beat --loglevel=info
```

A new background task follows the same shape: sync session factory, not the async one
used by request-handling code — mixing them is a common mistake when porting logic from
an endpoint/service into a Celery task.

## Apple Pay (`apple-services` extra — the one real toggle)

`app/services/payments/apple_pay.py` wraps `app-store-server-library[async]` for App
Store receipt/subscription verification, credentials modeled by
`ApplePayStoreCredentials` in `app/core/credentials.py`. It's the **only** integration
wrapped in `# --- APPLE_PAY_*_START/END ---` marker blocks across `pyproject.toml`
(extras + mypy overrides), `config.py` (settings + computed property), `credentials.py`,
`.env.example`, and `README.md` — meaning `post_gen.py` can surgically delete it when a
user opts out at generation time (see
[copier-template-mechanics.md](copier-template-mechanics.md)). It also builds a
**module-level singleton at import time** that eagerly PEM-parses its private key — this
is why `tests/conftest.py` has to generate throwaway credentials *before* any `app.*`
import (see [testing-conventions.md](testing-conventions.md)); the same import-time
fragility applies to any code that imports this module without valid (even if dummy)
credential files present.
