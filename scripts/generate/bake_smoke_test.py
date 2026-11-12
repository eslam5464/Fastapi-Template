"""Smoke tests for the copier template. Not part of the main test suite
(scripts/generate/ is excluded from testpaths) - run explicitly with:

    uv run pytest scripts/generate/bake_smoke_test.py
"""

import subprocess
import sys
from pathlib import Path

import copier
import pytest

TEMPLATE_ROOT = Path(__file__).resolve().parents[2]
if str(TEMPLATE_ROOT / "scripts" / "generate") not in sys.path:
    sys.path.insert(0, str(TEMPLATE_ROOT / "scripts" / "generate"))

import features  # noqa: E402


def _bake(dst: Path, **data) -> None:
    copier.run_copy(
        str(TEMPLATE_ROOT),
        str(dst),
        # Without this Copier bakes the latest release tag, so the test would
        # check the previous release instead of the code being changed.
        # "HEAD" includes uncommitted changes (the worktree state).
        vcs_ref="HEAD",
        data=data,
        defaults=True,
        unsafe=True,
        quiet=True,
    )


# Scoped to our own copier variable names rather than a blanket "{{"/"{%" scan:
# the app's own email templating (app/services/email/base.py, static/*.html)
# and GitHub Actions expressions in .github/workflows/*.yml legitimately use
# curly-brace syntax unrelated to copier.
_LEFTOVER_TOKENS = (
    "{{ project_name",
    "{{ project_slug",
    "{{ project_description",
    "{{ author_name",
    "{{ author_email",
    "{{ github_username",
    "{{ python_version",
    "{% if include_apple_pay",
    "{{ cookiecutter",
)


# The fastapi-template-architect skill ships into generated projects and its
# references quote copier.yml's `_tasks` verbatim (e.g. "{{ project_name }}") as
# documentation - that's intentional text, not an unrendered template. Its
# references/ dir likewise documents the marker syntax itself, so FEATURE[
# occurrences there are expected too.
_SKILL_DIRS = (
    Path(".claude"),
    Path(".agents"),
)


def _assert_no_leftover_jinja(root: Path) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if any(path.relative_to(root).is_relative_to(skill_dir) for skill_dir in _SKILL_DIRS):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, ValueError):
            continue
        for token in _LEFTOVER_TOKENS:
            assert token not in content, f"leftover Jinja syntax ({token!r}) in {path}"


def _assert_no_feature_markers(root: Path) -> None:
    """The marker engine must have consumed every FEATURE[ marker line."""
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if any(path.relative_to(root).is_relative_to(skill_dir) for skill_dir in _SKILL_DIRS):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, ValueError):
            continue
        assert "FEATURE[" not in content, f"leftover feature marker in {path}"


def _assert_no_tool_caches(root: Path) -> None:
    """Generation must not leave tool caches (e.g. from post_gen's ruff pass) behind."""
    leftovers = [name for name in (".ruff_cache", ".pytest_cache", ".mypy_cache") if (root / name).exists()]
    assert not leftovers, f"tool caches left in the generated project: {leftovers}"


def _assert_ruff_clean(root: Path) -> None:
    """The whole baked project must satisfy its own ruff config (lint + format),
    run via the same interpreter that runs this test so the tooling is
    guaranteed present."""
    for args in (["check", "."], ["format", "--check", "."]):
        result = subprocess.run(
            [sys.executable, "-m", "ruff", *args],
            cwd=root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"ruff {' '.join(args)} failed for baked project:\n{result.stdout}\n{result.stderr}"
        )


def _assert_full_project(dst: Path) -> None:
    # Every file or folder an optional feature owns is present; only the
    # template's own sections (the "_template" feature) stay out.
    for rel, expr in features.PATHS.items():
        if "_template" in expr:
            continue
        assert (dst / rel).exists(), f"{rel} should be in the full project"


def _assert_minimal_base(dst: Path) -> None:
    assert not (dst / "app" / "services" / "payments").exists()
    assert not (dst / "app" / "core" / "exceptions" / "apple_pay.py").exists()
    assert not (dst / "app" / "core" / "credentials" / "apple_pay.py").exists()
    assert not (dst / "tests" / "services" / "payments").exists()
    assert not (dst / "tests" / "apple_pay_credentials.py").exists()
    # Every file or folder an optional feature owns is gone; the shared packages stay.
    for rel in features.PATHS:
        assert not (dst / rel).exists(), f"{rel} should not be in the minimal base"
    assert (dst / "app" / "core" / "credentials" / "__init__.py").is_file()
    assert "FIREBASE_" not in (dst / ".env.example").read_text()
    assert "firebase" not in (dst / "app" / "core" / "config.py").read_text().lower()
    assert "app-store-server-library" not in (dst / "pyproject.toml").read_text()
    assert "APPLE_PAY" not in (dst / ".env.example").read_text()
    assert "apple_pay" not in (dst / "app" / "core" / "config.py").read_text()
    assert "apple_pay" not in (dst / "tests" / "conftest.py").read_text().lower()


@pytest.mark.slow
def test_bake_with_defaults(tmp_path: Path):
    dst = tmp_path / "generated"
    _bake(dst)

    assert (dst / "pyproject.toml").is_file()
    assert (dst / "app" / "main.py").is_file()
    assert (dst / "Dockerfile").is_file()
    _assert_full_project(dst)
    _assert_no_leftover_jinja(dst)
    _assert_no_feature_markers(dst)
    _assert_no_tool_caches(dst)
    _assert_ruff_clean(dst)


@pytest.mark.slow
def test_bake_minimal(tmp_path: Path):
    dst = tmp_path / "generated"
    _bake(dst, services="minimal")

    assert (dst / "pyproject.toml").is_file()
    assert (dst / "app" / "main.py").is_file()
    assert (dst / "Dockerfile").is_file()
    _assert_minimal_base(dst)
    _assert_no_leftover_jinja(dst)
    _assert_no_feature_markers(dst)
    _assert_no_tool_caches(dst)
    _assert_ruff_clean(dst)


@pytest.mark.slow
def test_bake_with_apple_pay(tmp_path: Path):
    dst = tmp_path / "generated"
    _bake(dst, services="custom", include_apple_pay=True)

    assert (dst / "app" / "services" / "payments" / "apple_pay.py").is_file()
    assert (dst / "app" / "core" / "credentials" / "apple_pay.py").is_file()
    assert (dst / "app" / "core" / "exceptions" / "apple_pay.py").is_file()
    assert (dst / "tests" / "apple_pay_credentials.py").is_file()
    assert "app-store-server-library" in (dst / "pyproject.toml").read_text()
    _assert_no_leftover_jinja(dst)
    _assert_no_feature_markers(dst)
    _assert_no_tool_caches(dst)
    _assert_ruff_clean(dst)


@pytest.mark.slow
def test_bake_rejects_stray_apple_pay(tmp_path: Path):
    dst = tmp_path / "generated"
    # With services pinned to minimal, a stray include_apple_pay=true must be
    # rejected by post_gen.py's answer validation instead of silently shipping
    # Apple Pay files in a minimal bake.
    with pytest.raises(Exception) as excinfo:
        _bake(dst, services="minimal", include_apple_pay=True)
    stderr = getattr(excinfo.value, "stderr", None)
    if stderr:
        assert "services=custom" in str(stderr)


@pytest.mark.slow
def test_project_slug_derivation(tmp_path: Path):
    dst = tmp_path / "generated"
    _bake(dst, services="minimal", project_name="My Cool App")

    pyproject = (dst / "pyproject.toml").read_text()
    assert 'name = "my-cool-app"' in pyproject

    env_example = (dst / ".env.example").read_text()
    assert "POSTGRES_DB_SCHEMA=my_cool_app" in env_example

    compose = (dst / "docker-compose.yml").read_text()
    assert "my_cool_app_backend" in compose
