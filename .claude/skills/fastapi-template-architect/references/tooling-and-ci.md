# Tooling & CI

Source: real `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `tach.toml`
(all snapshotted in `../assets/`), and `pyproject.toml` (not snapshotted — read it
directly in the target repo; its exact tool config blocks are described below from
direct inspection).

## `pyproject.toml` shape

- `requires-python = ">=3.14"` — the codebase actively uses 3.14+-only syntax (PEP 758
  multi-exception `except A, B:` without parens shows up for real in
  `app/services/auth_service.py` and `scripts/generate/post_gen.py`). Don't downgrade the
  Python version floor without also removing/rewriting that syntax.
- **Core dependencies** (always installed): fastapi, `sqlalchemy[asyncio]`, alembic,
  asyncpg, `psycopg[binary]`/psycopg (platform-split — async engine uses asyncpg, the
  sync engine used by Celery uses psycopg), pydantic/pydantic-settings, `pwdlib[argon2]`,
  pyjwt + python-jose, loguru, gunicorn, `uvicorn[standard]`, uvloop/httptools on
  non-Windows platforms, yarl.
- **Optional extras** (`uv sync --extra <name>`, see
  [optional-integrations.md](optional-integrations.md)): `email`, `cloud-service`,
  `cache`, `task-queue`, `apple-services`.
- **`dependency-groups`** (not extras — dev/test tooling, `uv sync --all-groups`):
  `test` (anyio, faker, httpx, pytest, pytest-cov), `dev` (bandit[toml], commitizen,
  detect-secrets, mypy, ruff, tach, types-aiofiles), `template` (copier — only relevant
  in the source template repo itself, not in generated projects).

### Ruff

`line-length = 120`, `target-version = "py314"`, `select = ["E", "F", "I", "W"]`,
`ignore = ["E501"]` (line length is enforced by the formatter, not the linter, hence the
explicit ignore). Per-file ignores for `__init__.py` (`F401`/`I001` — re-export files
legitimately have "unused" imports) and one specific pytest `importorskip` file
(`E402`).

### Mypy

`python_version = "3.14"`, `plugins = ["pydantic.mypy"]`. `disallow_untyped_defs = True`
is scoped **only** to `app.repos.*`, `app.models.*`, `app.services.*` via
`[[tool.mypy.overrides]]` — not the whole codebase. Additional overrides carve out
SDK-heavy wrapper modules (firebase/gcs/back_blaze_b2/apple_pay — third-party libs
without good stubs) from strict checking. Don't blanket-enable full strict mode across
`app/api` or `app/core` without checking these overrides first; that's a deliberate,
scoped strictness choice, not an oversight.

### Bandit

`exclude_dirs = ["tests", ".venv", "alembic/versions"]`. Run via
`uv run bandit -r app -f json -o bandit_results.json`, and as a pre-commit hook scoped to
`^app/`.

### Commitizen

`cz_conventional_commits`, `version_files = ["pyproject.toml:version"]`,
`tag_format = "$version"` — commit messages must follow Conventional Commits; the
`commitizen` pre-commit hook lints this at `commit-msg` stage only (requires a one-time
`pre-commit install --hook-type commit-msg`, separate from the default `pre-commit
install`).

### Coverage

`relative_files = true` — deliberately set because the coverage-comment CI action
re-reads `.coverage` from inside a different container path than where it was generated;
without this, path-based coverage merging breaks.

### Pytest

See [testing-conventions.md](testing-conventions.md) for the full picture —
`testpaths = ["tests"]`, `python_files = ["*_test.py"]`, `addopts` includes
`--cov=app --cov-report=html:htmlcov --no-cov-on-fail`, custom markers
`unit`/`integration`/`slow`/`websocket`.

## `tach.toml` — an enforced module-boundary graph, not just documentation

`../assets/tach.toml` declares the exact dependency graph matching
[layering-and-flow.md](layering-and-flow.md)'s import rules table:

```
core (nothing) → models/schemas (core) → repos (core, models, schemas)
  → services (core, models, schemas, repos) → api / middleware (+ services for api)
```

`app.main`, `app.web`, `app.alembic` are intentionally left **undeclared** — they're the
composition root and legitimately touch every layer. `tach check` runs as a local
pre-commit hook (`language: system`, needs the project's real venv to resolve `app.*`
imports) and again as a required CI check via `pre-commit run --all-files` — a genuine
layering violation fails the build, it isn't just a lint suggestion.

## `.pre-commit-config.yaml` — the full hook list

From `../assets/.pre-commit-config.yaml`:

1. Standard `pre-commit-hooks`: trailing-whitespace, end-of-file-fixer, check-yaml,
   check-added-large-files (`--maxkb=10240`), check-toml, detect-private-key,
   check-merge-conflict, `name-tests-test` (excluding `conftest.py`/`schemas.py`/
   `utils.py`).
2. `ruff` (`--fix`) + `ruff-format`, both excluding `app/alembic/versions/` (generated
   migration files aren't reformatted).
3. **Local hooks** (`language: system`, run through the project's own `uv`-managed venv
   rather than an isolated pre-commit environment): `mypy` and `tach check`. The
   deliberate reason: this project has 25+ runtime dependencies, and mirroring them all
   in pre-commit's `additional_dependencies` would drift from `pyproject.toml` over time.
   Requires `uv sync` to have been run locally first.
4. `bandit` (scoped to `^app/`).
5. `detect-secrets` against `.secrets.baseline` (excludes `uv.lock`, `htmlcov/`,
   `.venv/`, and rendered architecture-diagram HTML files).
6. `check-github-workflows` + `check-dependabot` (JSON-schema validation of workflow/
   dependabot YAML).
7. `commitizen` (`commit-msg` stage only).

`ci:` block: `pre-commit.ci` autofixes PRs and autoupdates hooks weekly, but explicitly
`skip: [mypy, tach]` there — pre-commit.ci's sandbox has no access to this project's venv,
so those two are enforced instead as required checks in `.github/workflows/ci.yml`'s
`lint` job (which runs the *exact same* `pre-commit run --all-files` locally-equivalent
command, just with real dependencies installed).

## `.github/workflows/` — what each one does

- **`ci.yml`** — two jobs. `lint`: installs `uv`, `uv sync --all-groups --all-extras
  --frozen`, caches `~/.cache/pre-commit`, runs `pre-commit run --all-files
  --show-diff-on-failure` as a required check (catches contributors who never installed
  pre-commit locally). `test`: real `postgres:18-alpine` + `redis:8-alpine` service
  containers, installs `libpq-dev` (needed because the sync/psycopg engine needs libpq at
  *import* time, matching the Dockerfile's `postgresql-dev`/`postgresql-libs`), copies
  `.env.example` → `.env` with a few `sed` overrides to match the service containers'
  credentials, creates a `_test`-suffixed database, runs `alembic upgrade head` then
  `pytest`, then posts a coverage PR comment (green ≥ 90%, orange ≥ 70%) via
  `py-cov-action/python-coverage-comment-action`.
- **`codeql.yml`** — Python CodeQL analysis on push/PR/weekly cron.
- **`dependency-review.yml`** — fails on `high`-severity or worse dependency
  vulnerabilities in a PR, posts a summary comment.
- **`dependabot.yml`** — `uv` ecosystem + `github-actions`, weekly, groups minor/patch
  updates, 3-day cooldown, reviewers sourced from `CODEOWNERS`.
- **`template-ci.yml`** (source-template repo only — excluded from generated projects,
  see [copier-template-mechanics.md](copier-template-mechanics.md)) — bakes the template
  with Copier across an `include_apple_pay: [true, false]` matrix and runs the
  **generated project's own test suite** as a smoke test. If you're extending the source
  template itself (not a generated project), any change must keep this workflow green in
  both matrix legs.

Apple Pay test-credential generation used to be a separate CI-only step in `ci.yml`; it
was removed in favor of `tests/conftest.py`'s self-contained, import-time
`_ensure_apple_pay_test_credentials()` (see
[testing-conventions.md](testing-conventions.md)) — the git history literally shows this
simplification (`"Remove unused APPLE_PAY_CI_MARKERS..."`, `"Refactor CI workflow and
remove Apple Pay credential generation step"`). Don't reintroduce a CI-only credential
step; the conftest approach already covers both local and CI runs identically.
