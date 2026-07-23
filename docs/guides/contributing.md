# Contributing

## Contribution Flow

1. Sync from master.
2. Create a focused branch.
3. Implement changes with tests.
4. Run lint, format, and tests.
5. Open PR with clear scope and validation notes.

## Code Standards

- Keep changes layer-aligned and minimal.
- Prefer explicit typing for public functions.
- Keep endpoint logic thin.
- Do not place business logic in middleware or routers.

## PR Checklist

- [ ] Scope is focused and documented
- [ ] Tests added or updated
- [ ] uv run pytest passes
- [ ] uv run pre-commit run --all-files passes (ruff, tach, mypy, bandit, detect-secrets, check-jsonschema)
- [ ] Docs updated (including docs/llms.txt when relevant)
- [ ] Breaking API changes called out clearly
- [ ] Commit messages follow Conventional Commits (enforced by the commitizen hook — see below)

## CI

Every PR runs, and must pass, all of the following before it's mergeable:

- `ci.yml` `lint` job — the same pre-commit hooks as the checklist above, run as a required check.
- `ci.yml` `test` job — pytest against real Postgres + Redis service containers, with a coverage diff posted as a PR comment.
- `codeql.yml` and `dependency-review.yml` — static security analysis and dependency vulnerability scanning.

`.github/CODEOWNERS` auto-requests review on every PR.

## Commit Messages

Commit messages are linted against [Conventional Commits](https://www.conventionalcommits.org/)
by the `commitizen` pre-commit hook (e.g. `fix: ...`, `feat: ...`, `docs: ...`, `chore: ...`).
This hook runs at the `commit-msg` git stage, which the default `pre-commit install` does not
wire up — run this once after cloning:

```bash
uv run pre-commit install --hook-type commit-msg
```

See [Versioning](versioning.md) for how this commit history drives release version bumps.
