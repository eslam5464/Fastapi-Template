# Copilot Instructions

This repository is FastAPI Template, a layered FastAPI backend with async SQLAlchemy, Redis-backed cache/rate limiting, and JWT auth.

Primary AI reference
- Read docs/llms.txt first for documentation map and canonical entry points.

Architecture rules
- Keep endpoints thin and move business logic to services.
- Keep database access in repositories.
- Deps layer owns request-scoped session wiring and transaction orchestration.
- Services raise domain exceptions; API translates to HTTP exceptions.

Current API versioning
- Root app has no global docs/openapi routes.
- Root operational endpoint: /health.
- Versioned mounted apps:
  - /v1 with /v1/docs, /v1/redoc, /v1/openapi.json
  - /v2 with /v2/docs, /v2/redoc, /v2/openapi.json

Developer commands
- Setup: uv sync --all-groups --all-extras
- Run: python main.py
- Tests: uv run pytest
- Format: uv run black --line-length=100 app && uv run isort --profile=black --line-length=100 app
- Type check: uv run mypy app --config-file=pyproject.toml
- Security lint: uv run bandit -c pyproject.toml -r app
- Secret scan: uv run detect-secrets scan --baseline .secrets.baseline
- All of the above at once: uv run pre-commit run --all-files

CI gates (.github/workflows/)
- ci.yml `lint` job: runs the same pre-commit hooks as above (black, isort, autoflake, mypy, bandit, detect-secrets) — required to pass before merge.
- ci.yml `test` job: pytest against real Postgres + Redis service containers, with a coverage PR comment.
- codeql.yml and dependency-review.yml: static security analysis and dependency vulnerability checks on every PR.
- .github/CODEOWNERS auto-requests review from @Eslam5464 on every PR, including Dependabot's.
- Any PR you open should pass all of the above before it's mergeable — don't add code that would fail mypy's moderate-strictness config (see `[tool.mypy]` overrides in pyproject.toml for exactly which modules require full type annotations) or introduce a bandit finding without a justified `# nosec` comment.

Code quality expectations
- Prefer explicit typing for public functions and tests.
- Add or update tests for behavior changes.
- Avoid broad refactors when making targeted fixes.
- Preserve existing logging and middleware ordering in app/main.py.
