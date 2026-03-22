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
- Setup: uv sync --all-groups
- Run: python main.py
- Tests: uv run pytest
- Lint: uv run ruff check .
- Format: uv run ruff format .

Code quality expectations
- Prefer explicit typing for public functions and tests.
- Add or update tests for behavior changes.
- Avoid broad refactors when making targeted fixes.
- Preserve existing logging and middleware ordering in app/main.py.
