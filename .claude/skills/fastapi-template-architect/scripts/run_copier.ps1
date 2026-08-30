<#
.SYNOPSIS
  Wrapper around `copier copy` for fastapi-template-architect's Generate Mode.

.DESCRIPTION
  Assembles the real copier.yml answers into one command instead of relying on
  copier's interactive prompts (which don't work well when Claude is driving this),
  and prints the follow-up `uv sync --extra ...` command for whatever optional
  integrations the caller chose. See ../SKILL.md and
  ../references/copier-template-mechanics.md for what each answer controls, and
  ../references/optional-integrations.md for why extras are separate from this.

.EXAMPLE
  ./run_copier.ps1 -Target C:\Users\me\projects\acme-orders `
    -ProjectName "Acme Orders" -ProjectSlug "acme-orders" `
    -ProjectDescription "Order management backend" `
    -AuthorName "Jane Doe" -AuthorEmail "jane@example.com" `
    -GithubUsername "janedoe" -PythonVersion "3.14" `
    -IncludeApplePay $false -Extras "email,cache"
#>

param(
    [Parameter(Mandatory = $true)][string]$Target,
    [string]$Source = "gh:eslam5464/Fastapi-Template",
    [Parameter(Mandatory = $true)][string]$ProjectName,
    [Parameter(Mandatory = $true)][string]$ProjectSlug,
    [string]$ProjectDescription = "",
    [string]$AuthorName = "",
    [string]$AuthorEmail = "",
    [string]$GithubUsername = "",
    [string]$PythonVersion = "3.14",
    [bool]$IncludeApplePay = $false,
    [string]$Extras = ""
)

$copierArgs = @(
    "copy", $Source, $Target, "--trust",
    "--data", "project_name=$ProjectName",
    "--data", "project_slug=$ProjectSlug",
    "--data", "author_name=$AuthorName",
    "--data", "author_email=$AuthorEmail",
    "--data", "github_username=$GithubUsername",
    "--data", "python_version=$PythonVersion",
    "--data", "include_apple_pay=$($IncludeApplePay.ToString().ToLower())"
)
if ($ProjectDescription) {
    $copierArgs += @("--data", "project_description=$ProjectDescription")
}

# Prefer `uv run copier` (the project's own pinned copier + full dependency set)
# when $Source is a local checkout with a uv-managed venv available - verified
# 2026-08-30 that bare `uvx copier` can fail with "No module named 'jinja2_time'"
# (a Jinja extension copier tries to load that isn't in its minimal ephemeral env);
# `uvx --with jinja2-time copier` is the fallback fix for the gh: remote case.
$localSourceUsable = $false
if ((Test-Path $Source) -and (Test-Path (Join-Path $Source "pyproject.toml"))) {
    Push-Location $Source
    try { & uv run copier --version *> $null; $localSourceUsable = ($LASTEXITCODE -eq 0) }
    catch { $localSourceUsable = $false }
    Pop-Location
}

if ($localSourceUsable) {
    Write-Host "Running: (cd '$Source'; uv run copier $($copierArgs -join ' '))"
    Push-Location $Source
    & uv run copier @copierArgs
    Pop-Location
} else {
    Write-Host "Running: uvx --with jinja2-time copier $($copierArgs -join ' ')"
    & uvx --with jinja2-time copier @copierArgs
}

# NOTE (verified 2026-08-30): generating from a *local* git checkout only picks up
# committed content - Copier resolves a local path source through git, so anything
# uncommitted (e.g. a freshly-added .claude/skills/) will NOT appear in the output,
# and the source repo's full git history can end up copied into the target's .git.
# Prefer the gh: remote for anything other than throwaway local testing, and make
# sure this skill itself is committed & pushed before relying on generated projects
# inheriting it.

Write-Host ""
Write-Host "Generation complete. Next steps:"
Write-Host "  cd '$Target'"
Write-Host "  uv sync --all-groups"
if ($Extras) {
    foreach ($e in $Extras -split ",") {
        Write-Host "  uv sync --extra $($e.Trim())"
    }
}
Write-Host "  pre-commit install"
Write-Host "  pre-commit install --hook-type commit-msg"
Write-Host "  Copy-Item .env.example .env   # then fill it in yourself - never let an assistant fill in secrets"
Write-Host "  createdb <db_name> ; alembic upgrade head"
