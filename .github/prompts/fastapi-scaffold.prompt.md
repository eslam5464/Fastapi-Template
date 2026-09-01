---
agent: 'agent'
description: 'Scaffold a new FastAPI backend using the Fastapi-Template layered architecture'
---

## Task

Scaffold a brand-new FastAPI backend by driving the real
[eslam5464/Fastapi-Template](https://github.com/eslam5464/Fastapi-Template) Copier
template — do not hand-write the boilerplate from memory, that's how it drifts from
what the template actually generates.

1. Locate the template: prefer a local checkout if one is available (a sibling
   directory containing `copier.yml`); otherwise use the GitHub remote,
   `gh:eslam5464/Fastapi-Template`.
2. Gather the real Copier answers from the conversation: `project_name`,
   `project_slug`, `project_description`, `author_name`, `author_email`,
   `github_username`, `python_version` (>=3.14), `include_apple_pay` (bool — the only
   real generation-time code-stripping toggle).
3. Separately ask which optional integrations are wanted — email, cache/Redis, cloud
   storage, task-queue. These are **not** Copier questions; they're `pyproject.toml`
   extras installed afterward with `uv sync --extra <name>`. Don't present them as
   generation-time code-removal choices.
4. Run generation:
   ```bash
   uv run copier copy <local-path> <target-dir> --trust
   # or, no local checkout:
   uvx --with jinja2-time copier copy gh:eslam5464/Fastapi-Template <target-dir> --trust
   ```
   `--trust` is required (generation runs `scripts/generate/post_gen.py` for identity
   substitution, license rewrite, optional Apple Pay removal, lockfile regen,
   `git init`). Bare `uvx copier` can fail with `No module named 'jinja2_time'` without
   `--with jinja2-time`. Generating from a **local** path only picks up **committed**
   content — an uncommitted change in the source checkout won't appear in the output.
5. Run the rest of the README Quick Start as an explicit post-gen checklist: `uv sync
   --all-groups` plus `--extra <name>` for each chosen integration, `pre-commit
   install` (and `--hook-type commit-msg`), have the user fill in `.env` themselves
   (never fill in secrets on their behalf), `createdb` + `alembic upgrade head`, and
   smoke-test `GET /v1/health` before declaring success.

Target: `${input:project_name:What should the new project be called?}`
