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


def _bake(dst: Path, **data) -> None:
    copier.run_copy(
        str(TEMPLATE_ROOT),
        str(dst),
        # Without this Copier bakes the latest release tag, so the test would
        # check the previous release instead of the code being changed.
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
# documentation - that's intentional text, not an unrendered template.
_SKILL_DIRS = (
    Path(".claude") / "skills",
    Path(".agents") / "skills",
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


def _assert_conftest_ruff_clean(root: Path) -> None:
    """The baked tests/conftest.py (Apple Pay block stripped) must satisfy the
    baked project's own ruff config, run via the same interpreter that runs this
    test so the tooling is guaranteed present."""
    conftest = root / "tests" / "conftest.py"
    for args in (["check", str(conftest)], ["format", "--check", str(conftest)]):
        result = subprocess.run(
            [sys.executable, "-m", "ruff", *args],
            cwd=root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"ruff {' '.join(args)} failed for baked tests/conftest.py:\n{result.stdout}\n{result.stderr}"
        )


@pytest.mark.slow
def test_bake_with_defaults(tmp_path: Path):
    dst = tmp_path / "generated"
    _bake(dst)

    assert (dst / "pyproject.toml").is_file()
    assert (dst / "app" / "main.py").is_file()
    assert (dst / "Dockerfile").is_file()
    assert (dst / "app" / "services" / "payments" / "apple_pay.py").is_file()
    assert (dst / "app" / "core" / "credentials" / "apple_pay.py").is_file()
    assert (dst / "tests" / "apple_pay_credentials.py").is_file()
    assert "apple-services" in (dst / "pyproject.toml").read_text()
    _assert_no_leftover_jinja(dst)


@pytest.mark.slow
def test_bake_without_apple_pay(tmp_path: Path):
    dst = tmp_path / "generated"
    _bake(dst, include_apple_pay=False)

    assert not (dst / "app" / "services" / "payments" / "apple_pay.py").exists()
    assert not (dst / "app" / "core" / "credentials" / "apple_pay.py").exists()
    assert (dst / "app" / "core" / "credentials" / "firebase.py").is_file()
    assert "apple-services" not in (dst / "pyproject.toml").read_text()
    assert not (dst / "app" / "core" / "exceptions" / "apple_pay.py").exists()
    assert not (dst / "tests" / "services" / "payments").exists()
    assert "apple_pay" not in (dst / "app" / "core" / "config.py").read_text()
    assert "APPLE_PAY" not in (dst / ".env.example").read_text()
    assert not (dst / "tests" / "apple_pay_credentials.py").exists()
    assert "apple_pay" not in (dst / "tests" / "conftest.py").read_text().lower()
    _assert_no_leftover_jinja(dst)
    _assert_conftest_ruff_clean(dst)


@pytest.mark.slow
def test_project_slug_derivation(tmp_path: Path):
    dst = tmp_path / "generated"
    _bake(dst, project_name="My Cool App")

    pyproject = (dst / "pyproject.toml").read_text()
    assert 'name = "my-cool-app"' in pyproject

    env_example = (dst / ".env.example").read_text()
    assert "POSTGRES_DB_SCHEMA=my_cool_app" in env_example

    compose = (dst / "docker-compose.yml").read_text()
    assert "my_cool_app_backend" in compose
