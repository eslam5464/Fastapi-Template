# Copier Template Mechanics

Source: `copier.yml`, `README.md`'s "Using This as a Template" section, and
`scripts/generate/post_gen.py` (read directly — verify against the live repo, since this
is the piece most likely to change as the template evolves; not snapshotted in
`../assets/` since it's inherently project-specific plumbing rather than a reusable
pattern to copy into a *generated* project).

## This is a Copier template, not Cookiecutter — and an unusual one

No `cookiecutter.json`, no `{{cookiecutter.*}}` placeholders, and critically: **no
`.jinja`-suffixed files anywhere in the source tree**. Most Copier templates render
Jinja syntax inside file contents or filenames. This one doesn't. Instead:

1. `copier copy` copies the repo **verbatim** — the result of a plain copy is already a
   complete, runnable, fully-tested application (because the source repo itself always
   stays runnable; there's no template-only broken intermediate state).
2. A post-generation Python script (`scripts/generate/post_gen.py`, invoked via
   `copier.yml`'s `_tasks:` hook) then does **literal string find-and-replace** on the
   concrete files it just copied — e.g. replacing the literal string `name =
   "FastApi-Template"` in `pyproject.toml` with the user's chosen project name.

This means the repo is simultaneously (a) a complete, directly-runnable reference app,
and (b) a Copier generator — with no Jinja templating layer to keep in sync between the
two. This is why Generate Mode in `../SKILL.md` prefers driving real Copier over
hand-writing files: there is no separate "template source" to fall behind the real app.

## The exact `copier.yml` question set (verify this against the live file before relying on it — it's the piece most likely to drift)

```yaml
project_name:      # str, default "FastAPI Template"
project_slug:       # str, auto-derived from project_name (lowercased, hyphenated)
project_description: # str, default "A production-ready FastAPI backend with async PostgreSQL, JWT auth, and clean architecture."
author_name:        # str, default "Eslam"
author_email:        # str, default "eslam5464@users.noreply.github.com"
github_username:     # str, default "eslam5464"
python_version:      # str, default "3.14"; validator enforces >= 3.14 (PEP 758 syntax requirement)
include_apple_pay:   # bool, default true — the ONLY real code-stripping toggle today

_exclude:
  - "copier.yml"
  - ".github/workflows/template-ci.yml"

_tasks:
  - ["{{ _copier_python }}", "scripts/generate/post_gen.py",
     "--project-name", "{{ project_name }}", "--project-slug", "{{ project_slug }}",
     "--project-description", "{{ project_description }}",
     "--author-name", "{{ author_name }}", "--author-email", "{{ author_email }}",
     "--github-username", "{{ github_username }}",
     "--python-version", "{{ python_version }}",
     "--include-apple-pay", "{{ include_apple_pay }}"]
```

Invocation (from `README.md`):

```bash
# uvx - no install needed, sidesteps Windows PATH issues entirely
uvx copier copy gh:eslam5464/Fastapi-Template <new-project-dir> --trust

# local checkout instead of the GitHub remote:
uv run copier copy <local-path> <new-project-dir> --trust
```

`--trust` is required because generation runs `post_gen.py`, which edits files and runs
`git init`/`uv lock` — Copier requires explicit trust to execute a template's tasks.

### Two gotchas verified empirically (2026-08-30), not documented in the README

1. **Bare `uvx copier copy ...` can fail outright** with `Copier could not load some
   Jinja extensions: No module named 'jinja2_time'` and exit non-zero — a fresh,
   ephemeral `uvx` install of `copier` can resolve a version/environment missing an
   optional Jinja extension copier tries to load, even though nothing in this template's
   `copier.yml` actually requires `jinja2-time`. Fix: `uvx --with jinja2-time copier copy
   ...`. Running via `uv run copier copy ...` from inside a checkout where `uv sync` has
   already been run does **not** hit this (the project's own resolved environment
   happens to carry it), which is one more reason to prefer a local checkout when one is
   available.
2. **Generating from a local path source only picks up git-committed content.** Copier
   resolves a local-path source through git rather than copying the raw working
   directory — so any uncommitted file (a freshly-added file, a work-in-progress change)
   silently does **not** appear in the generated output, with no error or warning. In the
   same test, the source repo's git history ended up inside the generated project's
   `.git` as well (post_gen.py's `git_init_and_commit()` step re-initializes but doesn't
   necessarily discard what was already cloned in). **Practical implication:** always
   commit (and for anything beyond local smoke-testing, push) changes to the source
   template — including to this very skill — before relying on local-path generation or
   on generated projects inheriting them; prefer the `gh:` remote, which fetches whatever
   was actually pushed, for anything other than throwaway local verification.

## `post_gen.py` — what actually happens after the copy, in order

1. **`bump_python_version`** — regex-substitutes the pinned Python version across
   `Dockerfile`, `docker-compose.yml`, `pyproject.toml`, three docs files,
   `.python-version`, and Ruff's `target-version`.
2. **`apply_identity_substitutions`** — literal replace across `pyproject.toml`,
   `docker-compose.yml`, `.env.example`, `.github/CODEOWNERS`,
   `.github/copilot-instructions.md`, `README.md`, `docs/development.md`,
   `docs/deployment.md`, `docs/guides/getting-started.md` — project name/slug/
   description, author name/email, GitHub username all land here.
3. **`rewrite_license`** — regex-extracts the old year/author from `LICENSE` and
   replaces them.
4. **`remove_apple_pay()`** (only if `include_apple_pay` was declined) — deletes
   `app/services/payments/apple_pay.py`, its exception module, and its test directory,
   then calls `strip_marked_block()` to cut every `# --- APPLE_PAY_*_START/END ---`
   region out of `config.py`, `credentials.py`, `.env.example`, `pyproject.toml` (extras
   list + mypy overrides). This is the **only** integration with real generation-time
   code removal — see the callout below.
5. **`strip_template_only_sections()`** — removes `TEMPLATE_TOOLING_*`-marked blocks
   (the `template` dependency-group, i.e. `copier` itself, and any commitizen-dev-only
   marked section) and the `<!-- TEMPLATE_SECTION_START/END -->`-marked "Using This as a
   Template" block from the generated project's `README.md` — a generated project's
   README doesn't tell its own users how to re-template it from itself.
6. **`regenerate_lockfile()`** — `uv python install <version>` + `uv lock`, tolerant of
   failure (doesn't hard-fail generation if the network/toolchain isn't available at
   generation time).
7. **`remove_generate_tooling()`** — the script deletes its own containing directory
   (`scripts/generate/`) as its last act — a generated project doesn't ship the
   generator that built it.
8. **`git_init_and_commit()`** — `git init && git add -A && git commit -m "chore:
   initial commit from copier template"` in the generated project.

## The marker-comment convention

A lightweight, purely textual, greppable alternative to Jinja `{% if %}` blocks, used for
conditional inclusion instead of real templating:

- Python: `# --- <FEATURE>_START ---` / `# --- <FEATURE>_END ---`
- Markdown: `<!-- TEMPLATE_SECTION_START -->` / `<!-- TEMPLATE_SECTION_END -->`

If you're extending this template with a new generation-time toggle, follow this same
convention rather than introducing Jinja templating into the source tree — that would
break the "the repo is always directly runnable" property that makes this whole approach
work.

## ⚠️ The distinction that matters most: toggle vs. extra

**Only `include_apple_pay` removes code at generation time.** Email, cache/Redis, cloud
storage (GCS/Backblaze/Firebase), and task-queue/Celery are **not** Copier questions —
they are `pyproject.toml` optional-dependency extras (`uv sync --extra email`, `--extra
cache`, etc., see [optional-integrations.md](optional-integrations.md)). Their source
code ships in **every** generated project regardless of what the user says they want;
"selecting" them really means choosing which extras to install and which `.env` block to
fill in, not code removal. Never tell a user "I'll generate the project without email
support" as if that were a Copier-level choice — the honest framing is "I won't install
the `email` extra or set up its config, but the code will still be present in the
generated project if you want it later."

## `template-ci.yml` — the self-verification loop

Bakes the template with Copier across an `include_apple_pay: [true, false]` matrix
(`uv run copier copy . /tmp/baked --data include_apple_pay=... --defaults --trust
--quiet`), greps the baked output for leftover Jinja syntax (defensive, since this
template shouldn't have any), then installs dependencies and **runs the generated
project's own full test suite** as the actual verification. This workflow is excluded
from generated projects (`_exclude` in `copier.yml`) — it only makes sense in the source
template repo itself. If the skill's Generate Mode is ever wrong about how generation
behaves, this workflow (and actually baking a throwaway project locally) is the fastest
way to verify the truth against the live template rather than trusting this document.
