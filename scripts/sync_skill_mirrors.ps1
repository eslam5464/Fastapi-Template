# Thin wrapper around scripts/sync_skill_mirrors.py - see that file for what it does.
#
# Usage:
#   scripts/sync_skill_mirrors.ps1           # regenerate the Codex CLI mirror
#   scripts/sync_skill_mirrors.ps1 -Check    # fail if the mirror is stale (used by pre-commit)

param(
    [switch]$Check
)

$RepoRoot = Split-Path -Parent $PSScriptRoot
$PyArgs = @()
if ($Check) { $PyArgs += "--check" }

uv run --project $RepoRoot python "$RepoRoot/scripts/sync_skill_mirrors.py" @PyArgs
exit $LASTEXITCODE
