# Development Guide

## Daily Workflow

1. Create a branch from master.
2. Implement focused changes by layer (API -> deps -> service -> repo).
3. Add or update tests in the same change.
4. Run lint/format/tests before opening PR.

## Branch Naming

- feature/<short-description>
- fix/<short-description>
- chore/<short-description>

## Commit Convention

Use concise imperative messages.
Examples:

- feat: mount versioned v2 docs app
- fix: whitelist docs CSP in security headers
- docs: align architecture with mounted versioning

## Quality Commands

```bash
uv run ruff check .
uv run ruff format .
uv run pytest
```

## Layering Rules

- Endpoints stay thin.
- Deps assemble services and own session boundaries.
- Services hold business rules and raise domain exceptions.
- Repositories perform data access only.

## Local Docs

- /v1/docs and /v2/docs are the canonical interactive docs endpoints.
- Root /docs is intentionally disabled.
