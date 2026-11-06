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
services:            # choice: "minimal" (default) or "custom"
include_firebase:    # bool, default false, asked only when services == custom
include_firestore:   # bool, default false, asked only when include_firebase is true
include_gcs:         # bool, default false, asked only when services == custom
include_backblaze:   # bool, default false, asked only when services == custom
include_apple_pay:   # bool, default false, asked only when services == custom

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
     "--features-json", "{{ {'services': services, 'include_firebase': include_firebase, 'include_firestore': include_firestore, 'include_gcs': include_gcs, 'include_backblaze': include_backblaze, 'include_apple_pay': include_apple_pay} | tojson }}"]
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
   `Dockerfile`, `pyproject.toml`, three docs files,
   `.python-version`, and Ruff's `target-version`.
2. **`apply_identity_substitutions`** — literal replace across `pyproject.toml`,
   `docker-compose.yml`, `.env.example`, `.github/CODEOWNERS`,
   `.github/copilot-instructions.md`, `README.md`, `docs/development.md`,
   `docs/deployment.md`, `docs/guides/getting-started.md` — project name/slug/
   description, author name/email, GitHub username all land here.
3. **`rewrite_license`** — regex-extracts the old year/author from `LICENSE` and
   replaces them.
4. **`resolve()`** — validates the `--features-json` answers against
   `scripts/generate/features.py` (the feature manifest): with `services=minimal` every
   `include_*` must be false (a stray `--data include_x=true` is an error, not silently
   ignored).
5. **`markers.apply()`** — the marker engine (`scripts/generate/markers.py`) deletes the
   files and directories the manifest's `PATHS` maps to a disabled feature, cuts every
   `FEATURE[...]` block whose expression is false (including the `_template` blocks:
   the `template` dependency group and the README's "Using This as a Template" section),
   then `normalize_python()` re-sorts imports and re-formats the Python files it changed.
6. **`regenerate_lockfile()`** — `uv python install <version>` + `uv lock`, tolerant of
   failure (doesn't hard-fail generation if the network/toolchain isn't available at
   generation time; `FASTAPI_TEMPLATE_STRICT=1` makes it fatal).
7. **`remove_generate_tooling()`** — the script deletes its own containing directory
   (`scripts/generate/`) as its last act — a generated project doesn't ship the
   generator that built it.
8. **`git_init_and_commit()`** — `git init && git add -A`, then
   `refresh_secrets_baseline()` (re-runs the pinned detect-secrets hook so
   `.secrets.baseline` line numbers match the stripped files), then
   `git commit -m "chore: initial commit from copier template"`.

## The marker-comment convention

A purely textual, greppable alternative to Jinja `{% if %}` blocks, processed by
`scripts/generate/markers.py`. Markers are whole lines; the END line repeats the START
expression:

- `#`-comment files (Python, TOML, YAML, `.env.example`, Dockerfile, shell):
  `# --- FEATURE[backblaze] START ---` / `# --- FEATURE[backblaze] END ---`
- Markdown/HTML: `<!-- --- FEATURE[backblaze] START --- -->` / `<!-- --- FEATURE[backblaze] END --- -->`
- Expressions: a feature name, `a|b`, `a&b`; `!a` only in Markdown/HTML. Blocks nest.

Every feature name must exist in `scripts/generate/features.py`, which also lists the
files each feature owns (`PATHS`), its allowed third-party imports and the tokens that
must not survive when it is off. Never put markers inside docstrings, Markdown tables or
code fences.

If you're extending this template with a new generation-time toggle, follow this same
convention rather than introducing Jinja templating into the source tree — that would
break the "the repo is always directly runnable" property that makes this whole approach
work.

## ⚠️ The distinction that matters most: toggle vs. extra

**Services with an `include_*` question remove their code at generation time** when
declined (today: Firebase, Firestore, Google Cloud Storage, BackBlaze B2 and Apple Pay). Email, cache/Redis and
task-queue/Celery are still `pyproject.toml` optional-dependency extras (`uv sync --extra
email`, `--extra cache`, etc., see [optional-integrations.md](optional-integrations.md))
whose source code ships in **every** generated project; "selecting" one of those means
choosing which extras to install and which `.env` block to fill in, not code removal.
Never tell a user "I'll generate the project without email support" as if that were a
Copier-level choice for an extra — say "I won't install the `email` extra or set up its
config, but the code will still be present if you want it later."

## `template-ci.yml` — the self-verification loop

Builds its bake matrix from the feature manifest (`scripts/generate/variants.py
--matrix`: `minimal`, `full`, each feature alone and full-minus-each-feature, with
duplicates removed), so a new feature gets its bake jobs without editing the workflow.
Each `bake` job generates its variant with `scripts/generate/bake.py` (the real Copier
flow, strict mode), greps for leftover Jinja and `FEATURE[...]` markers, checks the bake
against the manifest (`check_variants.py --tree`: import closure, forbidden tokens of
disabled features, ruff), imports every app module with production dependencies only,
runs the generated project's own pre-commit hooks, migrations and **full test suite**
(failing on any skipped test), and boots the app to call `/health`. Other jobs run the
generator's unit tests and the offline checker, the same tests on Python 3.9 (Copier's
oldest supported interpreter), a Windows bake, and a Docker compose smoke test for
`minimal` and `full`. This workflow is excluded from generated projects (`_exclude` in
`copier.yml`) — it only makes sense in the source template repo itself. If the skill's
Generate Mode is ever wrong about how generation behaves, reproduce a job locally with
`uv run python scripts/generate/bake.py --variant <name> --dest ../baked` rather than
trusting this document.
