# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

## [Unreleased]

### Fixed

- Added missing Celery worker/beat scripts (`scripts/celery_worker.sh`, `scripts/celery_worker.bat`, `scripts/celery_beat.sh`, `scripts/celery_beat.bat`) referenced in README and docs
- Moved `pre-commit` from runtime dependencies to the `dev` dependency group in `pyproject.toml`
- Removed unused `security_bcrypt_rounds` setting from `app/core/config.py` (passwords use Argon2 via pwdlib)
- Changed `ACCESS_TOKEN_EXPIRE_SECONDS` default from 2582000 to 3600 (1 hour) in `.env.example`; renamed `resend_api_key` / `brevo_api_key` to `RESEND_API_KEY` / `BREVO_API_KEY` for consistent `UPPER_SNAKE_CASE` across `.env.example`, `README.md`, and docs
- Fixed smoke-test health endpoint URL from `/v1/health` to `/health` in skill documentation and prompts; updated skill version to 1.0.1
- Dockerfile: `COPY ./app ./` with `WORKDIR /app` flattened the package so `uvicorn app.main:app` could not import `app`; the app now copies to `/app/app`, and `alembic.ini` + `pyproject.toml` are copied into the production stage (`alembic upgrade head` in CMD failed with `No 'script_location' key found`, and `app/core/config.py` reads `pyproject.toml` at startup)
- Dockerfile: HEALTHCHECK probed `http://127.0.0.1:8080/`; it now probes `http://127.0.0.1:8799/health`, matching the app's port and health route
- Dockerfile: production stage now installs `binutils` and creates the `libpq.so` symlink so `ctypes.util.find_library("pq")` can locate libpq on musl — the pure-Python `psycopg` wrapper raised `ImportError: libpq library not found` at import time (`postgresql-dev` would add ~500 MB; this adds ~25 MB)
- Dockerfile: `uv sync --frozen --no-dev` did not install `redis` (it lives in the optional `cache` extra), so importing `app/services/cache/*` crashed the container at startup; the sync now includes `--extra cache`
- `docker-compose.yml`: backend `image: python:3.14-alpine` made the build retag the upstream base image locally (poisoning every later `FROM python:3.14-alpine` build with the app's layers and non-root USER); the built image is now named `fastapi_template_backend`
- `docker-compose.yml`: db healthcheck `["CMD-SHELL", "pg_isready", "-d", "${POSTGRES_DB}"]` silently dropped every argument after the first; it now runs a single-string `pg_isready -U $POSTGRES_USER -d $POSTGRES_DB` against the configured user/db
- `docker-compose.yml`: backend `environment:` omitted settings `app/core/config.py` requires (Firebase, Redis, cache TTLs, rate-limit flag, Apple Pay, data seeding, email keys), failing pydantic validation at startup; the backend now receives the full environment from the env file with only `POSTGRES_HOST=db` and `REDIS_HOST=redis` overridden for the compose network
- `docker-compose.yml`: Redis ran without authentication (`REDIS_PASSWORD` is ignored by the redis image) and published port 6379 to the host; Redis now enforces auth matching what the app sends (`--requirepass` plus an ACL user from `REDIS_USER`/`REDIS_PASS`, verified via `redis_url` in `app/core/config.py`) and keeps port 6379 inside the compose network
- `app/main.py` parsed `ALLOWED_HOSTS` into `settings.allowed_hosts_list` but never enforced it; Starlette's `TrustedHostMiddleware` now runs with that list (no `"*"`), `127.0.0.1` was added to `ALLOWED_HOSTS` in `.env.example` so the container HEALTHCHECK passes, and the test client in `tests/conftest.py` targets `http://localhost` (covered by new allowed/disallowed host tests in `tests/main_test.py`)
- CI: new `docker` job in `.github/workflows/ci.yml` runs the clean-checkout compose smoke test (`cp .env.example .env.docker-test`, `up --build -d`, bounded wait loop, `curl -f /health`, healthy-status check, `down -v`) and prints `docker compose logs` on failure
- `docker-compose.yml`: `db` and `redis` restarted forever on failure (`restart: unless-stopped`) and their health checks ran every 30s after a 30-80s start period, so a misconfigured service crash-looped for minutes before showing as unhealthy; restarts are now capped (`on-failure:5`, the backend keeps its existing `deploy.restart_policy` cap) and health checks run every 5s after a 10s start period
- `scripts/generate/bake_smoke_test.py`: the leftover-Jinja scan flagged the bundled skill's documentation, which quotes `copier.yml` verbatim; the scan now skips `.claude/skills` and `.agents/skills` in the generated project
- Dockerfile: the HEALTHCHECK probed `127.0.0.1` with that address as its Host header, so any `ALLOWED_HOSTS` without `127.0.0.1` (for example a production hostname) left the container permanently unhealthy; the probe now sends the first configured allowed host as its Host header
- `docker-compose.yml`: the `db` volume was mounted at `/var/lib/postgresql/data`, which current `postgres:18` images reject at startup (they store data under `/var/lib/postgresql/<major>/`); the volume is now mounted at `/var/lib/postgresql`
- `scripts/generate/post_gen.py` still expected a pinned Python version in `docker-compose.yml` after the backend image was renamed, failing every `copier copy`; the file was dropped from the version-bump list
- `scripts/generate/bake_smoke_test.py` and the Template CI workflow now bake `--vcs-ref HEAD`; without it Copier bakes the latest release tag, so local bake tests were checking the previous release instead of the working tree

## [1.2.0] - 2026-09-01

### Fixed

- `scripts/generate/post_gen.py` no longer tries to substitute project-name/`@Eslam5464` text into `.github/copilot-instructions.md`; that file was rewritten to be generic and no longer contains either, so every `copier copy` bake was failing with `expected content not found`.
- `copier.yml`'s `_exclude` list now restores Copier's built-in default excludes (`.git`, `__pycache__`, `.DS_Store`, etc.) alongside the template's own entries. Defining `_exclude` replaces Copier's defaults rather than extending them, so generated projects were silently shipping this template's entire git history.

## [1.1.1] - 2026-07-24

### Changed

- Bumped the project's minimum required Python version from 3.13 to 3.14 (`pyproject.toml`, `Dockerfile`, `docker-compose.yml`, `.python-version`, mypy config, and docs).
- Upgraded `asyncpg` to `0.31.0`, the first release with prebuilt Windows wheels for Python 3.14 (0.30.0 only builds from source there and fails without the MSVC toolchain).

### Fixed

- `scripts/generate/post_gen.py` now proactively installs the requested Python interpreter before regenerating `uv.lock`, and suppresses benign git line-ending warnings during the post-generation commit, instead of letting raw `uv`/`git` output leak to the console during `copier copy`.

## [1.1.0] - 2026-07-23

### Added

- Copier-based project generation support (`copier.yml`, `.jinja` template files, `scripts/generate/`) — this repo can now generate new FastAPI projects from itself while remaining directly runnable at its own root.
- `docs/features.md` documenting the full list of integrations and services, with setup notes.
- `docs/guides/versioning.md` describing the SemVer workflow and how to bump releases, manually or via `cz bump`.
- Standards-aligned docs structure under docs/architecture, docs/api, docs/guides, docs/strategy, and docs/changelog.
- llms index file and project AI instruction file.

### Changed

- Trimmed `README.md`'s Features/Dependencies sections to headline items, pointing to `docs/features.md` for full detail.
- Documented mounted API versioning model (/v1 and /v2) and per-version docs endpoints.
- Reconciled `pyproject.toml`'s version field with the actual git tag release history (had been stuck at `0.1.0` since it was introduced; corrected to `1.0.16` ahead of this release) and wired `commitizen` to keep the two in sync going forward.

### Fixed

- `tests/repos/base_repo_test.py` now reads the Postgres schema from `settings` instead of a hardcoded string.

## [0.1.0] - 2026-03-22

### Added

- Initial FastAPI template baseline with layered architecture, JWT auth, async SQLAlchemy, and middleware stack.
