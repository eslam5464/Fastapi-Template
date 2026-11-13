# Testing Conventions

Source: `docs/backend-architecture.md` ("Testing Strategy", "Pytest Implementation
Appendix"; when the project was generated with it) plus the real `tests/conftest.py` (snapshotted in `../assets/`).

## File naming — `*_test.py`, not `test_*.py`

Enforced via `[tool.pytest.ini_options] python_files = ["*_test.py"]` in
`pyproject.toml`. Allowed: `auth_service_test.py`. Prohibited: `test_auth_service.py`.
This is the opposite of the pytest-community default convention — don't assume a
generic pytest tutorial's naming applies here. `.pre-commit-config.yaml`'s
`name-tests-test` hook enforces this too, with an explicit exclude for
the helper modules (`conftest.py`, `sample_model.py`, `schemas.py`, `utils.py`).

## Test layout in this repo (vs. the architecture doc's ideal)

The architecture doc's Pytest Appendix recommends a `tests/{unit,integration,e2e}/`
split. **This repo's actual `tests/` directory mirrors `app/`'s structure instead**
(e.g. `tests/services/auth_service_test.py`, not `tests/unit/auth_service_test.py`) —
a documented gap between the generic guidance and this repo's reality. When adding
tests here, follow the existing mirror-`app/`-structure convention, not the doc's ideal
layout, unless the user explicitly asks to migrate to the `unit/integration/e2e` split.

**One optional service per test file.** Code for an optional service (Redis cache, rate
limiting, token blacklist, Celery, Firebase/Firestore, GCS, BackBlaze, email providers,
Apple Pay, OpenObserve) is tested only in files that belong to that service, so a
generated project that leaves the service out can drop those files whole:
`tests/services/<service>/` packages with their own `conftest.py` (the shared
`tests/services/conftest.py` holds only SDK-free fixtures), `tests/main_cache_test.py` /
`main_rate_limit_test.py` / `main_token_blacklist_test.py` beside the base
`tests/main_test.py`, and `tests/api/v1/deps/token_revocation_test.py` /
`endpoints/logout_revocation_test.py` for revocation. Base tests never patch a service
object: `tests/api/conftest.py` replaces the token blacklist with an in-memory
`FakeTokenBlacklist` for every API test, and `tests/utils.py`'s `mock_lifespan_steps()`
mocks every per-service startup check and shutdown step of `app/main.py`. No test may
skip: a missing SDK must fail the run, so never use `pytest.importorskip`.

## `anyio`, not `pytest-asyncio`

The `anyio` fixture is defined explicitly in `conftest.py` (`anyio_backend` fixture
returning `"asyncio"`) — `pyproject.toml` notes this was previously a transitive
dependency and has been made explicit. Don't add `pytest-asyncio` or `@pytest.mark.
asyncio` decorators; async test functions here work via the `anyio` pytest plugin
picking up the `anyio_backend` fixture automatically.

## Fixture naming convention

- `mock_<thing>` — mock/fake dependency (e.g. `mock_resource_repo`).
- `<thing>_factory` — a fixture returning a callable that generates data.
- `<thing>` — a real-instance fixture (e.g. `user`, `db_session`, `client`).

## Fixtures live next to what they need

- `tests/conftest.py` holds only fixtures every project has: `anyio_backend`,
  `test_app`, `client`, `faker`, `db_session` and `sample_record`.
- `tests/sample_model.py` defines a test-only model (`SampleRecord`, its schemas and
  `SampleRecordRepo`). The generic layers (`Base`, `BaseRepository`) are tested through
  it in `tests/models/base_model_test.py` and `tests/repos/base_repo_test.py`, so those
  tests don't depend on a domain model. `conftest.py` imports it, which registers its
  table for `create_all`; Alembic never sees it.
- `tests/api/v1/conftest.py` (projects with auth) holds the user and token fixtures (`user`, `other_user`,
  `token`, `pre_hashed_password`, `default_password`) for the tests of the authenticated
  API.

## The mounted-apps dependency-override gotcha

Because `app/main.py` mounts each versioned API as a **separate** FastAPI instance
under `app` (see [api-governance.md](api-governance.md)), a dependency override on `app`
alone does **not** reach routes served through the mounted sub-apps. The real
`test_app` fixture in `../assets/tests/conftest.py` applies every override to the root
app and to every mounted sub-app, through its `mounted_apps()` helper:

```python
for mounted_app in mounted_apps():
    mounted_app.dependency_overrides[get_session] = override_get_session
```

...and clears them all on teardown. Use `mounted_apps()` (or the sub-app itself, e.g.
`v1_app`) for any new dependency override — overriding only `app` produces tests that
pass for root-level routes but hit the real database/service for every versioned
endpoint, which is easy to miss because the test doesn't error, it just silently uses
production wiring.

## The "expensive singleton at import time" trick

In a project with Apple Pay, `tests/conftest.py` opens with
`ensure_apple_pay_test_credentials()` (defined in `tests/apple_pay_credentials.py`),
called at **module import time**, before any `app.*` import (projects without Apple Pay
have neither the call nor the module):

```python
from tests.apple_pay_credentials import ensure_apple_pay_test_credentials

ensure_apple_pay_test_credentials()

from typing import AsyncGenerator  # noqa: E402

import pytest  # noqa: E402
...
from app.main import app  # noqa: E402
```

Why: `app/services/payments/apple_pay.py` builds a module-level `ApplePay()` singleton
that eagerly PEM-parses a private key **at import time**. A fixture would run too late —
the crash happens during test *collection*, before any fixture executes. Generating the
throwaway credentials as a plain module-level function call before the `app.*` imports
(with `# noqa: E402` on those now-deferred imports) is the general-purpose pattern for
**any** module that does expensive/fragile work as an import-time side effect: do the
prerequisite setup before importing the module, at conftest module scope, not in a
fixture. This runs identically locally and in CI — no separate CI-only credential step
needed (a prior CI-only mechanism for this was removed; see
[copier-template-mechanics.md](copier-template-mechanics.md) if that history matters).

## Expensive setup, computed once

`pre_hashed_password` is a **session-scoped** fixture that hashes the shared test
password with Argon2 exactly once for the whole test session, rather than re-hashing per
test — Argon2 is deliberately slow, and re-paying that cost per test measurably slows the
suite. Reuse this fixture (or the same pattern) for any new test that needs a hashed
credential; don't call the password hasher directly inside a per-test fixture.

`test_app` (function-scoped) creates a **fresh async engine per test function** with
`poolclass=NullPool` and an explicit `await test_engine.dispose()` in a `finally` block.
`NullPool` + explicit disposal matters here specifically because the engine is
short-lived (one per test) — without it, the suite accumulates pooled connections across
hundreds of tests and can hit `max_connections`, especially under CI's tighter resource
limits. Follow this pattern for any new fixture that spins up its own engine.

## Unit / integration / E2E — what goes where

- **Unit** (mocked services): inject `AsyncMock()` repos into a service constructor
  directly — no patching needed, since repos are already externally injected. Assert
  against domain exceptions (`pytest.raises(ValidationError, match=...)`), not error
  result objects.
- **Integration** (real test DB): exercise a repository against `db_session`/`test_app`'s
  real (test) database — validates actual SQL behavior, constraints, and query
  correctness that mocks can't catch.
- **E2E** (`client` fixture, `httpx.AsyncClient` via `ASGITransport`): exercise the full
  request lifecycle through the actual FastAPI app — auth, middleware, serialization,
  everything.

## Definition-of-Done checklists

**API endpoint**: explicit request/response schemas + `response_model` · delegates to an
injected service · maps documented domain exceptions to HTTP exceptions · final `except
Exception` + `logger.exception(...)` · documents error responses in OpenAPI `responses`.

**Dependency function**: owns the request-scoped session via `Depends(get_session)` ·
wires repos/services only (no domain rules) · uses explicit commit/rollback when
coordinating atomic operations · never leaks a raw session into a service.

**Service method**: `TypedDict`-first contracts from `app/services/types/` · business
validation lives here · raises domain exceptions, never HTTP exceptions · Google-style
docstring with a `Raises` section and `arg_name (Type): description` formatting.

**Repository method**: persistence-only (no business rules) · exposes `auto_commit` on
mutation methods · parameterized SQL/ORM expressions only · has an integration test for
any custom query.

## CI execution model

`ci.yml`'s `test` job spins up a **real** `postgres:18-alpine` service container, plus
`redis:8-alpine` in projects with a Redis-backed service (not mocks/sqlite) — copies `.env.example` → `.env`, overrides a few values
via `sed` to match the service containers' credentials, creates a `_test`-suffixed
database, runs `alembic upgrade head`, then `pytest`, then posts a coverage PR comment
(green ≥ 90%, orange ≥ 70%). Local development should match this: run against a real
Postgres (and Redis, when the project has it), not a lighter substitute, since the
app's async engine, schema-scoped metadata, and Redis-backed services
(cache/rate-limit/blacklist) all assume the real thing.
