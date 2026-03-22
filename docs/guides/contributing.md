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
- [ ] uv run ruff check . passes
- [ ] uv run ruff format . applied
- [ ] Docs updated (including docs/llms.txt when relevant)
- [ ] Breaking API changes called out clearly
