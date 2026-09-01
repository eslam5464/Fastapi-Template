#!/usr/bin/env bash
# Thin wrapper around scripts/sync_skill_mirrors.py - see that file for what it does.
#
# Usage:
#   scripts/sync_skill_mirrors.sh           # regenerate the Codex CLI mirror
#   scripts/sync_skill_mirrors.sh --check   # fail if the mirror is stale (used by pre-commit)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec uv run --project "$REPO_ROOT" python "$REPO_ROOT/scripts/sync_skill_mirrors.py" "$@"
