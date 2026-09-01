---
name: fastapi-template-architect
description: >-
  Scaffold a brand-new FastAPI backend using this repo's production-grade layered
  architecture (API/Deps/Service/Repository/Model, async SQLAlchemy 2.0, JWT auth,
  Alembic, Docker, CI), or keep an existing project built on this architecture
  compliant with it as it grows. Use whenever the user wants to start a new FastAPI
  project, "scaffold" / "bootstrap" / "generate" a FastAPI backend, generate a
  project from the eslam5464/Fastapi-Template Copier template, add a new
  endpoint/service/repository/model/migration to a project that already follows
  this architecture, or review FastAPI code for layering, exception-handling, or
  SQLAlchemy relationship violations. Trigger even when the user doesn't name the
  template explicitly but describes wanting a clean layered FastAPI architecture,
  a repository pattern, "best practices" FastAPI structure, or asks "does this
  follow the architecture" / "is this a god service" / "where should this code go."
metadata:
  version: "1.0.0"
  author: eslam5464
  source_repo: eslam5464/Fastapi-Template
---

# FastAPI Template Architect

This skill packages the layered architecture, patterns, and generation mechanics of
[eslam5464/Fastapi-Template](https://github.com/eslam5464/Fastapi-Template) — a
production-grade FastAPI backend that is simultaneously a working reference app and a
[Copier](https://copier.readthedocs.io/) template. It has two modes. Work out which one
applies before doing anything else.

## Mode router

Look at the target working directory:

- **It already has `app/{api,core,models,schemas,repos,services}` and a `tach.toml`**
  (this repo itself, or a project generated from it) → **Extend/Audit Mode**. The user
  is adding to, or asking about the correctness of, an existing instance of this
  architecture.
- **It's empty, doesn't exist yet, or the user explicitly asks to start/scaffold/
  generate/bootstrap a new project** → **Generate Mode**.
- Ambiguous (e.g. a non-empty directory that isn't this architecture, or the user's
  intent is unclear)? Ask directly rather than guessing — the two modes produce very
  different actions.

## Generate Mode — scaffold a new project

**Do not hand-write the boilerplate from memory.** The whole point of this mode is to
drive the *real*, tested Copier template rather than re-deriving ~100 files from prose,
which is exactly how architectural details drift and go stale. Only fall back to
hand-building (see "Offline fallback" below) when Copier genuinely isn't usable.

1. **Locate the template.** Prefer a local checkout: ask the user, or check if a sibling
   directory (e.g. next to the target, or a path they mention) already contains this
   repo — `copier.yml` at its root confirms it. If no local checkout is available or
   reachable, use the GitHub remote.

2. **Gather the real Copier answers from the conversation.** Read
   [references/copier-template-mechanics.md](references/copier-template-mechanics.md)
   for the exact question set and what each answer controls. In short: `project_name`,
   `project_slug`, `project_description`, `author_name`, `author_email`,
   `github_username`, `python_version` (≥3.14), `include_apple_pay` (bool — the only
   real code-stripping toggle today).

3. **Separately, ask which optional integrations the user actually wants** — email,
   cache/Redis, cloud storage (GCS/Backblaze/Firebase), task-queue/Celery. These are
   **not** Copier questions; they're `pyproject.toml` extras. See
   [references/optional-integrations.md](references/optional-integrations.md) before
   answering the user's questions about them, and don't present them as if they were
   generation-time code-removal choices — that would misrepresent what the template
   actually does. Apple Pay is the one exception: it really is stripped at generation
   time when declined.

4. **Run generation** — prefer [scripts/run_copier.sh](scripts/run_copier.sh) /
   [scripts/run_copier.ps1](scripts/run_copier.ps1), which already encode the two fixes
   below, over typing the command by hand:
   ```bash
   # Local checkout (also the more reliable option — see caveat below):
   uv run copier copy <local-path> <target-dir> --trust
   # No local checkout — GitHub remote:
   uvx --with jinja2-time copier copy gh:eslam5464/Fastapi-Template <target-dir> --trust
   ```
   `--trust` is required because generation runs `scripts/generate/post_gen.py` (identity
   substitution, license rewrite, optional Apple-Pay removal, lockfile regen, `git init`).
   **Two verified gotchas, don't skip them:** bare `uvx copier copy ...` can fail with
   `No module named 'jinja2_time'` — a fresh `uvx` install of copier can be missing an
   optional Jinja extension it tries to load; `--with jinja2-time` fixes it. And
   generating from a **local** path only picks up **committed** content (Copier resolves
   a local source through git) — an uncommitted change in the source checkout silently
   won't appear in the generated output, and prefer the `gh:` remote for anything beyond
   throwaway local testing. See
   [references/copier-template-mechanics.md](references/copier-template-mechanics.md)
   for the full detail.

5. **Run the rest of the README Quick Start as an explicit post-gen checklist** (don't
   skip steps or assume the user did them):
   - `uv sync --all-groups` plus `uv sync --extra <name>` for each integration chosen in
     step 3 (or `--all-extras` if the user wants everything installed).
   - `pre-commit install` (and `pre-commit install --hook-type commit-msg` for the
     Commitizen commit-msg hook).
   - Tell the user to copy `.env.example` to `.env` and fill it in themselves — **never
     fill in secrets or credentials on their behalf**, per the standing safety rules on
     entering credentials.
   - `createdb <db_name>` then `alembic upgrade head`.
   - Optionally `docker compose up` if they want the containerized path instead.
   - Smoke-test: `GET /v1/health` (or start the app and hit it) to confirm the generated
     project actually runs before declaring success.

6. **Offline fallback** (no network, no Copier, no local checkout): use
   [assets/](assets/) (curated real files) plus the other `references/*.md` files to
   hand-build the structure. Tell the user explicitly that this path is a fallback with
   materially higher drift risk than driving real Copier, since it re-derives files
   instead of reusing tested ones.

## Extend/Audit Mode — work inside an existing instance of this architecture

This mode covers two distinct workflows. Work out which one the user actually wants
before doing anything: "add X" / "implement Y" is **Extending**; "review this," "does
this follow our architecture," "check this diff/PR," or handing over a file/diff/branch
without an explicit ask to change it, is **Reviewing**. If it's genuinely ambiguous,
default to Reviewing — presenting findings and asking before touching code is always the
safer default than guessing someone wants edits applied.

Route to the specific reference file(s) that match the task instead of loading
everything — that's the whole reason the knowledge is split up:

| Task | Read |
|---|---|
| New endpoint, request/response wiring, exception→HTTP mapping | [layering-and-flow.md](references/layering-and-flow.md), [api-governance.md](references/api-governance.md) |
| New model, relationship, many-to-many, migration | [repository-and-model-patterns.md](references/repository-and-model-patterns.md), [alembic-migration-safety.md](references/alembic-migration-safety.md) |
| New service or repository, schema design | [schema-and-service-patterns.md](references/schema-and-service-patterns.md) |
| Auth, CSRF, rate limiting, security headers | [auth-and-security.md](references/auth-and-security.md) |
| Logging, metrics, latency/query budgets | [observability-and-performance.md](references/observability-and-performance.md) |
| Writing or reviewing tests | [testing-conventions.md](references/testing-conventions.md) |
| CI, pre-commit, ruff/mypy/bandit config, `tach.toml` | [tooling-and-ci.md](references/tooling-and-ci.md) |
| Adding/removing an optional integration | [optional-integrations.md](references/optional-integrations.md) |
| Reviewing code, a diff, or "does this follow the architecture?" | [anti-patterns-catalog.md](references/anti-patterns-catalog.md) **plus** [layering-and-flow.md](references/layering-and-flow.md) |

### Extending — writing new code that follows the architecture

1. Identify which layer(s) the change touches and confirm the import-direction rule in
   `layering-and-flow.md` isn't being violated (lower layers never import from higher
   ones; services never see sessions; API is the exception-translation boundary).
2. Apply the canonical exception-contract matrix when adding error handling.
3. Keep new code's naming, docstring style (Google-style, no docstrings on endpoint
   functions), and file placement consistent with what's already in the project, even
   where a reference doc's example uses different placeholder names.
4. **When a reference doc's "canonical" description doesn't match what the target repo
   actually does, follow the real code.** E.g. `layering-and-flow.md` documents a
   `deps/services.py` file consolidating every `get_*_service()` factory as the
   architecture guide's canonical target — but the real repo doesn't have that file today;
   each domain's own deps file (`deps/auth.py`, etc.) defines its factory inline. Real,
   existing code always wins over a reference doc's aspirational description of where the
   project is headed.

### Reviewing — auditing existing code, a diff, or a whole codebase

A strict, findings-first workflow. **Never modify code as part of a review unless the
user has separately asked you to apply the fixes.** The review's job is to hand the user
a clear, honest account of what's wrong and what to do about it, then let *them* decide —
they may want none, some, or all of it fixed, and that's their call to make, not
something to resolve quietly by editing.

For every issue found:

1. **Name the anti-pattern plainly** — cite the specific rule/anti-pattern number from
   `anti-patterns-catalog.md` when one applies. Don't soften an actual MUST-rule
   violation into "you might consider..." — say it's wrong and why, the same directness
   the catalog itself uses.
2. **Point at the exact location** — file, line/function.
3. **State the concrete consequence** — what breaks, what becomes untestable, what fails
   silently (e.g. "this is silent data loss," not "this could be improved").
4. **Give the specific suggested fix** — real code or a concrete instruction, not a vague
   direction.

Structure the response as a numbered list of findings, worst/most-structural first, and
close by handing the choice back explicitly — e.g. "Reply with which of these you'd like
me to fix (by number, 'all', or 'none') and I'll only touch what you ask for." Do not
edit anything after a review until the user responds with that choice. If the code
genuinely checks out, say so plainly too — don't manufacture findings to look thorough.

## One important caveat for both modes

The `assets/` files and the reference docs' code examples are patterns, not a
lockstep copy-paste target. A target project's specifics (its project name, DB schema
name, actual domain models) still need real substitution and adaptation — never paste
an asset file in verbatim without checking it matches the target project's own
settings/imports/domain, even when Copier itself isn't in the loop.
