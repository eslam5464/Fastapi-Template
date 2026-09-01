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
uv run ruff check --fix app
uv run ruff format app
uv run mypy app --config-file=pyproject.toml
uv run tach check
uv run bandit -c pyproject.toml -r app
uv run pytest
```

Or run everything at once (matches the CI `lint` job exactly):

```bash
uv run pre-commit run --all-files
```

## Managing Detected Secrets

`.secrets.baseline` records every secret-shaped string the `detect-secrets` pre-commit hook (and CI) has already seen and reviewed — anything it finds that *isn't* in there fails the check.

Pull new or changed findings into the baseline for review:

```bash
uv run detect-secrets scan --baseline .secrets.baseline
```

Then step through the unaudited findings interactively, marking each one `y` (real secret) or `n` (false positive):

```bash
uv run detect-secrets audit .secrets.baseline
```

Commit `.secrets.baseline` afterward — it only protects anyone else once it's pushed.

**Note:** for a one-off false positive you can instead add an inline `# pragma: allowlist secret` comment on that line, and for a whole machine-generated file (whose "secret" is really just something like an embedded commit hash that changes every time it's regenerated) prefer extending the `exclude` regex on the `detect-secrets` hook in `.pre-commit-config.yaml` instead of re-auditing a moving target on every regeneration.

## Layering Rules

- Endpoints stay thin.
- Deps assemble services and own session boundaries.
- Services hold business rules and raise domain exceptions.
- Repositories perform data access only.

## Local Docs

- /v1/docs and /v2/docs are the canonical interactive docs endpoints.
- Root /docs is intentionally disabled.
