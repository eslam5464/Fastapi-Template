# Versioning

This project follows [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`).

## The rule, in plain terms

- **MAJOR** — something breaks for existing consumers of the running app's HTTP API (`/v1`, `/v2`): an endpoint or field is removed, renamed, or changed in a way that isn't backward compatible.
- **MINOR** — new functionality that doesn't break anything: a new endpoint, a new optional integration, a new feature flag.
- **PATCH** — a backward-compatible bug fix. No new behavior, just something broken made correct.

When in doubt: if a consumer's existing code could break, it's MAJOR. If they get something new but nothing old changes, it's MINOR. If nothing changes except a bug going away, it's PATCH.

## Where the version lives

`pyproject.toml`'s `[project].version` is the single source of truth. `app/core/config.py` reads it at runtime (via `tomllib`) and exposes it as `app_version`, which shows up in the running app — Swagger UI, the health check response. The git tag for a release should always match this value exactly (e.g. version `1.1.0` → tag `1.1.0`).

## Bumping manually

1. Decide the bump type (MAJOR/MINOR/PATCH) using the rule above.
2. Update `version` in `pyproject.toml`.
3. Add a new section to [`docs/changelog/CHANGELOG.md`](../changelog/CHANGELOG.md) above the previous release, following the existing [Keep a Changelog](https://keepachangelog.com/) format already used there:

   ```markdown
   ## [x.y.z] - YYYY-MM-DD

   ### Added
   - ...

   ### Changed
   - ...

   ### Fixed
   - ...
   ```

   Move anything sitting under `## [Unreleased]` into this new section if it belongs to the release.
4. Commit: `git commit -m "chore(release): x.y.z"`.
5. Tag: `git tag x.y.z`.
6. Push both: `git push && git push origin x.y.z`.

## Bumping automatically with commitizen

`pyproject.toml`'s `[tool.commitizen]` block is configured with `version_files` and `tag_format`, so `cz bump` can do steps 2–5 above for you by reading the Conventional Commit history since the last tag:

- A `feat:` commit anywhere in the range triggers a MINOR bump.
- A `fix:` commit (with no `feat:` present) triggers a PATCH bump.
- A `BREAKING CHANGE:` footer in any commit body triggers a MAJOR bump.

Preview what it would do before committing to it:

```bash
uv run cz bump --dry-run
```

Then run it for real:

```bash
uv run cz bump
```

This updates `pyproject.toml`, updates `docs/changelog/CHANGELOG.md`, and creates the git tag locally. You still need to push it yourself:

```bash
git push && git push --tags
```

Commit messages are already linted against Conventional Commits by the `commitizen` pre-commit hook — see [Contributing](contributing.md#commit-messages) — so by the time you run `cz bump`, the history it reads is already well-formed.

## Worked example: 1.0.16 → 1.1.0

The copier/cookiecutter conversion (adding `copier.yml`, `.jinja` template files, `scripts/generate/`, plus a docs reorganization and a small test bugfix) is a MINOR bump:

- Not MAJOR: nothing about the running app's HTTP API changed — no endpoint, field, or behavior was removed or altered for existing consumers.
- Not PATCH: it isn't a bug fix, it's new capability — this repo can now generate new projects from itself, which it couldn't do before.
- MINOR fits: new, backward-compatible functionality. Hence `1.0.16` → `1.1.0`.
