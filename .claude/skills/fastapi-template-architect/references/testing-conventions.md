# Testing Conventions

Source: `docs/backend-architecture.md` ("Testing Strategy", "Pytest Implementation
Appendix") plus the real `tests/conftest.py` (snapshotted in `../assets/`).

## File naming — `*_test.py`, not `test_*.py`

Enforced via `[tool.pytest.ini_options] python_files = ["*_test.py"]` in
`pyproject.toml`. Allowed: `auth_service_test.py`. Prohibited: `test_auth_service.py`.
This is the opposite of the pytest-community default convention — don't assume a
generic pytest tutorial's naming applies here. `.pre-commit-config.yaml`'s
`name-tests-test` hook enforces this too, with an explicit exclude for
`tests/(conftest|schemas|utils)\.py`.

## Test layout in this repo (vs. the architecture doc's ideal)

The architecture doc's Pytest Appendix recommends a `tests/{unit,integration,e2e}/`
split. **This repo's actual `tests/` directory mirrors `app/`'s structure instead**
(e.g. `tests/services/auth_service_test.py`, not `tests/unit/auth_service_test.py`) —
a documented gap between the generic guidance and this repo's reality. When adding
tests here, follow the existing mirror-`app/`-structure convention, not the doc's ideal
layout, unless the user explicitly asks to migrate to the `unit/integration/e2e` split.

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

## The three-app dependency-override gotcha

Because `app/main.py` mounts `v1_app` and `v2_app` as **separate** FastAPI instances
under `app` (see [api-governance.md](api-governance.md)), a dependency override on `app`
alone does **not** reach routes served through the mounted sub-apps. The real
`test_app` fixture in `../assets/tests/conftest.py` applies every override to all three
explicitly:

```python
app.dependency_overrides[get_session] = override_get_session
v1_app.dependency_overrides[get_session] = override_get_session
v2_app.dependency_overrides[get_session] = override_get_session
```

...and clears all three on teardown. Copy this pattern for any new dependency override
— forgetting `v1_app`/`v2_app` produces tests that pass for root-level routes but hit the
real database/service for every versioned endpoint, which is easy to miss because the
test doesn't error, it just silently uses production wiring.

## The "expensive singleton at import time" trick

`../assets/tests/conftest.py` opens with `_ensure_apple_pay_test_credentials()`, called
at **module import time**, before any `app.*` import:

```python
def _ensure_apple_pay_test_credentials() -> None:
    """Generate throwaway Apple Pay test credentials before any `app.*` module is imported. ..."""
    ...

_ensure_apple_pay_test_credentials()

import pytest  # noqa: E402
...
from app.main import app, v1_app, v2_app  # noqa: E402
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

`ci.yml`'s `test` job spins up **real** `postgres:18-alpine` and `redis:8-alpine` service
containers (not mocks/sqlite) — copies `.env.example` → `.env`, overrides a few values
via `sed` to match the service containers' credentials, creates a `_test`-suffixed
database, runs `alembic upgrade head`, then `pytest`, then posts a coverage PR comment
(green ≥ 90%, orange ≥ 70%). Local development should match this: run against a real
Postgres + Redis, not a lighter substitute, since the app's async engine, schema-scoped
metadata, and Redis-backed services (cache/rate-limit/blacklist) all assume the real
thing.
