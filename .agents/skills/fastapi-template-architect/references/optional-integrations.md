# Optional Integrations

Source: `pyproject.toml` optional-dependency extras, `.env.example`, `docs/features.md`,
and the relevant `app/services/*` modules. None of these modules are snapshotted in
`../assets/` (they're feature-specific, not architecturally load-bearing the way the
base classes/middleware are) — **read the actual file in the target repo before
modifying one**; what's below is a map of what exists and how to reason about it, not a
substitute for the real source.

## The rule that governs this whole file

**The extras below are not Copier generation-time toggles** — only the services with an
`include_*` question are (today `include_firebase`, `include_firestore`, `include_gcs`,
`include_backblaze`, `include_resend`, `include_brevo`, `include_openobserve`,
`include_celery`, `include_redis_rate_limit`, `include_redis_token_blacklist` and
`include_apple_pay`, see
[copier-template-mechanics.md](copier-template-mechanics.md)). Their code ships in every
generated project regardless. "Enabling" one of these for a project means: install its
`uv sync --extra <name>`, and fill in its `.env` config block. Don't present installing
an extra as equivalent to "generating the project with/without" that feature.

| Integration | Extra name | Key modules | Default behavior with no config |
|---|---|---|---|
| Email | — (Copier toggles `include_resend`, `include_brevo`) | `app/services/email/{base,resend,brevo}.py` | Not usable until an API key is set; no silent fallback |
| Cache (Redis) | `cache` | `app/services/cache/{base,manager,decorators,rate_limiter,token_blacklist}.py` | Fails open / no-op in `LOCAL` |
| Firebase, Firestore, GCS, BackBlaze | — (Copier toggles, below) | `app/services/{firebase,firestore,gcs,back_blaze_b2}.py` | Not usable until credentials are set |
| Task queue | — (Copier toggle `include_celery`) | `app/services/task_queue/{celery_config.py, tasks/user_tasks.py}` | Inert unless a worker/beat process is actually started |
| Apple Pay | `apple-services` | `app/services/payments/apple_pay.py` | **Removable at generation time** — the one real toggle |

## Email (Copier toggles, not an extra)

`app/services/email/base.py` defines `BaseEmailService(ABC)` with an abstract `send()`
and a concrete `send_welcome()` helper that renders `static/welcome.html` via a naive
`{{key}}` string-replace (not a real templating engine — don't assume Jinja syntax works
in that HTML file). Two provider adapters, chosen by which API key is configured:
`resend.py` (wraps the sync `resend` SDK via `asyncio.to_thread`, since the SDK itself is
sync) and `brevo.py`. This is the one service in this repo that genuinely uses the
**abstract-base-with-multiple-implementations** pattern from
[schema-and-service-patterns.md](schema-and-service-patterns.md) — appropriate here
specifically because there are two real interchangeable providers. Config: `.env.example`
has `RESEND_API_KEY` / `BREVO_API_KEY` — note these are now **uppercase**, consistent with
the rest of the file's `UPPER_SNAKE_CASE` convention. Each provider is its own Copier
toggle (`include_resend`, `include_brevo`); the shared base, types and exceptions ship
when at least one is chosen, and the chosen SDKs are core dependencies (guide:
`docs/integrations/email.md`).

## Cache / rate limiting / token blacklist (`cache` extra, Redis-backed)

The token blacklist is the `include_redis_token_blacklist` Copier toggle (without it,
logout returns `revoked: false` and tokens stay valid until they expire).
Rate limiting is the `include_redis_rate_limit` Copier toggle: without it,
`rate_limiter.py`, the rate-limit dependencies and middleware, `RateLimitPrefix`,
`app/core/types.py` and the `RATE_LIMIT_*` settings are not generated.

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

## Cloud storage & Firebase (Copier toggles, not extras)

- `app/services/gcs.py` — Google Cloud Storage via `gcloud-aio-storage`, schema in
  `app/schemas/google_bucket.py`. Not an extra: it is the `include_gcs` Copier toggle,
  and a project that includes it gets `gcloud-aio-storage` and `aiofiles` as core
  dependencies (guide: `docs/integrations/gcs.md`).
- `app/services/back_blaze_b2.py` — Backblaze B2 SDK, schema in
  `app/schemas/back_blaze_bucket.py`. Not an extra: it is the `include_backblaze`
  Copier toggle, and a project that includes it gets `b2sdk` as a core dependency
  (guide: `docs/integrations/backblaze.md`).
- `app/services/firebase.py` (Admin SDK auth) and `firestore.py` (Firestore DB) —
  the `include_firebase` and `include_firestore` Copier toggles (Firestore only with
  Firebase). A project that includes Firebase gets `firebase-admin` as a core
  dependency and the `FIREBASE_*` settings (`settings.firebase_credentials`, modeled by
  `FirebaseServiceAccount` in `app/core/credentials/firebase.py`, which supports either a
  raw key string or a file-path-based key and auto-escapes `\n` → `\\n` for a PEM key
  embedded directly in an env var). Guides: `docs/integrations/firebase.md` and
  `docs/integrations/firestore.md`.
- Each has its own exception module under `app/core/exceptions/` (`gcs_exceptions.py`,
  `back_blaze_exceptions.py`, `firebase_exceptions.py`) — note these live in `app/core/`
  rather than `app/services/exceptions/`, a documented deviation from the strict-profile
  domain-exception placement (same category of deviation as the `AppException`
  compatibility shim — see [layering-and-flow.md](layering-and-flow.md)).

## Task queue / background jobs (`include_celery` Copier toggle, Celery + Redis)

Included only when the project is generated with `include_celery`; it then gets
`celery[redis]`, `psycopg` and `faker` as core dependencies, the worker/beat scripts
and `app/core/db_sync.py` (guide: `docs/integrations/celery.md`).

`app/services/task_queue/celery_config.py` defines a `beat_schedule` dict typed with a
`CeleryTaskSettings` `TypedDict`. The one sample scheduled task,
`seed_fake_users_task` (`app/services/task_queue/tasks/user_tasks.py`), runs every 10
seconds when `ENABLE_DATA_SEEDING=true`, using the **sync** session factory
(`session_factory` from `app/core/db_sync.py` — Celery workers are sync, not async) to bulk
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
