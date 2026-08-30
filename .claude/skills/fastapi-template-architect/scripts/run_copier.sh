#!/usr/bin/env bash
# Wrapper around `copier copy` for fastapi-template-architect's Generate Mode.
#
# Assembles the real copier.yml answers into one command instead of relying on
# copier's interactive prompts (which don't work well when Claude is driving this),
# and prints the follow-up `uv sync --extra ...` command for whatever optional
# integrations the caller chose. See ../SKILL.md and
# ../references/copier-template-mechanics.md for what each answer controls, and
# ../references/optional-integrations.md for why extras are separate from this.
#
# Usage:
#   run_copier.sh --target <dir> [--source <local-path-or-gh-ref>] \
#     --project-name "<name>" --project-slug "<slug>" \
#     --project-description "<description>" \
#     --author-name "<name>" --author-email "<email>" \
#     --github-username "<username>" --python-version "3.14" \
#     --include-apple-pay <true|false> \
#     [--extras "email,cache"]
#
# Defaults: --source gh:eslam5464/Fastapi-Template (used when no local checkout
# is available). Pass a local path (e.g. the sibling directory of this repo) to
# avoid a network dependency and get the freshest local state.

set -euo pipefail

SOURCE="gh:eslam5464/Fastapi-Template"
# `uvx copier` alone resolves a fresh, minimal copier install that can be missing
# jinja2-time (an optional Jinja extension copier tries to load) and fails outright
# with "No module named 'jinja2_time'" - verified 2026-08-30. `--with jinja2-time`
# fixes it without needing copier installed persistently.
UVX_COPIER=(uvx --with jinja2-time copier)
EXTRAS=""
TARGET=""
PROJECT_NAME=""
PROJECT_SLUG=""
PROJECT_DESCRIPTION=""
AUTHOR_NAME=""
AUTHOR_EMAIL=""
GITHUB_USERNAME=""
PYTHON_VERSION="3.14"
INCLUDE_APPLE_PAY="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --source) SOURCE="$2"; shift 2 ;;
    --project-name) PROJECT_NAME="$2"; shift 2 ;;
    --project-slug) PROJECT_SLUG="$2"; shift 2 ;;
    --project-description) PROJECT_DESCRIPTION="$2"; shift 2 ;;
    --author-name) AUTHOR_NAME="$2"; shift 2 ;;
    --author-email) AUTHOR_EMAIL="$2"; shift 2 ;;
    --github-username) GITHUB_USERNAME="$2"; shift 2 ;;
    --python-version) PYTHON_VERSION="$2"; shift 2 ;;
    --include-apple-pay) INCLUDE_APPLE_PAY="$2"; shift 2 ;;
    --extras) EXTRAS="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$TARGET" || -z "$PROJECT_NAME" || -z "$PROJECT_SLUG" ]]; then
  echo "Required: --target, --project-name, --project-slug" >&2
  exit 1
fi

COPIER_ARGS=(copy "$SOURCE" "$TARGET" --trust
  --data "project_name=${PROJECT_NAME}"
  --data "project_slug=${PROJECT_SLUG}"
  --data "author_name=${AUTHOR_NAME}"
  --data "author_email=${AUTHOR_EMAIL}"
  --data "github_username=${GITHUB_USERNAME}"
  --data "python_version=${PYTHON_VERSION}"
  --data "include_apple_pay=${INCLUDE_APPLE_PAY}"
)
if [[ -n "$PROJECT_DESCRIPTION" ]]; then
  COPIER_ARGS+=(--data "project_description=${PROJECT_DESCRIPTION}")
fi

# Prefer `uv run copier` (the project's own pinned copier + full dependency set)
# when SOURCE is a local checkout with a uv-managed venv available - this is what
# actually worked in verification (2026-08-30); `uvx copier` alone hit the
# jinja2-time failure above even with the fix applied in some environments.
if [[ -d "$SOURCE" && -f "$SOURCE/pyproject.toml" ]] && (cd "$SOURCE" && uv run copier --version) >/dev/null 2>&1; then
  echo "Running: (cd '$SOURCE' && uv run copier ${COPIER_ARGS[*]})"
  (cd "$SOURCE" && uv run copier "${COPIER_ARGS[@]}")
else
  echo "Running: ${UVX_COPIER[*]} ${COPIER_ARGS[*]}"
  "${UVX_COPIER[@]}" "${COPIER_ARGS[@]}"
fi

# NOTE (verified 2026-08-30): generating from a *local* git checkout only picks up
# committed content - Copier resolves a local path source through git, so anything
# uncommitted (e.g. a freshly-added .claude/skills/) will NOT appear in the output,
# and the source repo's full git history can end up copied into the target's .git.
# Prefer the gh: remote for anything other than throwaway local testing, and make
# sure this skill itself is committed & pushed before relying on generated projects
# inheriting it.

echo ""
echo "Generation complete. Next steps:"
echo "  cd '${TARGET}'"
echo "  uv sync --all-groups"
if [[ -n "$EXTRAS" ]]; then
  IFS=',' read -ra EXTRA_LIST <<< "$EXTRAS"
  for e in "${EXTRA_LIST[@]}"; do
    echo "  uv sync --extra ${e}"
  done
fi
echo "  pre-commit install"
echo "  pre-commit install --hook-type commit-msg"
echo "  cp .env.example .env   # then fill it in yourself - never let an assistant fill in secrets"
echo "  createdb <db_name> && alembic upgrade head"
