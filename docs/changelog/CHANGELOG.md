# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog.

## [Unreleased]

## [1.1.0] - 2026-07-23

### Added

- Copier-based project generation support (`copier.yml`, `.jinja` template files, `scripts/generate/`) — this repo can now generate new FastAPI projects from itself while remaining directly runnable at its own root.
- `docs/features.md` documenting the full list of integrations and services, with setup notes.
- `docs/guides/versioning.md` describing the SemVer workflow and how to bump releases, manually or via `cz bump`.
- Standards-aligned docs structure under docs/architecture, docs/api, docs/guides, docs/strategy, and docs/changelog.
- llms index file and project AI instruction file.

### Changed

- Trimmed `README.md`'s Features/Dependencies sections to headline items, pointing to `docs/features.md` for full detail.
- Documented mounted API versioning model (/v1 and /v2) and per-version docs endpoints.
- Reconciled `pyproject.toml`'s version field with the actual git tag release history (had been stuck at `0.1.0` since it was introduced; corrected to `1.0.16` ahead of this release) and wired `commitizen` to keep the two in sync going forward.

### Fixed

- `tests/repos/base_repo_test.py` now reads the Postgres schema from `settings` instead of a hardcoded string.

## [0.1.0] - 2026-03-22

### Added

- Initial FastAPI template baseline with layered architecture, JWT auth, async SQLAlchemy, and middleware stack.
