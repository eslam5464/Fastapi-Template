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
   `github_username`, `python_version` (>=3.14), and `services`: `minimal`
   (the base, pre-selected in an interactive run), `custom`, or `full`
   (everything; what `--defaults` selects).
3. With `services=custom`, each optional service is its own yes/no question (all
   default to no) and a declined service is stripped from the generated project:
   `include_auth` (JWT auth with the User model), `include_example_items` (an example
   CRUD domain), `include_api_v2` (an empty `/v2`
   scaffold), `include_csrf` (the CSRF middleware), `include_redis_cache`,
   `include_redis_rate_limit`, `include_redis_token_blacklist` (only with auth),
   `include_celery`, `include_firebase`, `include_firestore` (only with Firebase),
   `include_gcs`, `include_backblaze`, `include_resend`, `include_brevo`,
   `include_openobserve`, `include_apple_pay`. Redis is never asked: it is added when
   the cache, rate limiting, the token blacklist or Celery is chosen. Point out that
   without auth every route is public, without rate limiting no route has a request
   limit, and without the token blacklist logout cannot revoke tokens.
4. Run generation, passing each chosen service as `--data`:
   ```bash
   uv run copier copy <local-path> <target-dir> --trust      --data services=custom --data include_redis_cache=true
   # or, no local checkout:
   uvx --with jinja2-time copier copy gh:eslam5464/Fastapi-Template <target-dir> --trust
   ```
   `--trust` is required (generation runs `scripts/generate/post_gen.py` for identity
   substitution, license rewrite, removal of the services that weren't chosen,
   lockfile regen, `git init`). If you use `--defaults` to skip the prompts, always pass
   `--data services=...` explicitly too: `--defaults` alone selects `full`, so the
   minimal base is `copier copy ... --defaults --data services=minimal`, and any other
   choice is `--defaults --data services=custom --data include_x=true`. Bare `uvx copier`
   can fail with `No module named 'jinja2_time'` without `--with jinja2-time`. Generating
   from a **local** path only picks up **committed** content — an uncommitted change in
   the source checkout won't appear in the output.
5. Run the rest of the README Quick Start as an explicit post-gen checklist:
   `uv sync --all-groups` (a chosen service's packages are regular dependencies, there
   are no extras), `pre-commit install` (and `--hook-type commit-msg`), have the user
   fill in `.env` themselves (never fill in secrets on their behalf), `createdb` +
   `alembic upgrade head`, and smoke-test `GET /health` before declaring success.

Target: `${input:project_name:What should the new project be called?}`
