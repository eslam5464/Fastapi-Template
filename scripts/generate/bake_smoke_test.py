"""Smoke tests for the copier template. Not part of the main test suite
(scripts/generate/ is excluded from testpaths) - run explicitly with:

    uv run pytest scripts/generate/bake_smoke_test.py
"""

from pathlib import Path

import copier
import pytest

TEMPLATE_ROOT = Path(__file__).resolve().parents[2]


def _bake(dst: Path, **data) -> None:
    copier.run_copy(
        str(TEMPLATE_ROOT),
        str(dst),
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


def _assert_no_leftover_jinja(root: Path) -> None:
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, ValueError):
            continue
        for token in _LEFTOVER_TOKENS:
            assert token not in content, f"leftover Jinja syntax ({token!r}) in {path}"


@pytest.mark.slow
def test_bake_with_defaults(tmp_path: Path):
    dst = tmp_path / "generated"
    _bake(dst)

    assert (dst / "pyproject.toml").is_file()
    assert (dst / "app" / "main.py").is_file()
    assert (dst / "Dockerfile").is_file()
    assert (dst / "app" / "services" / "payments" / "apple_pay.py").is_file()
    assert "apple-services" in (dst / "pyproject.toml").read_text()
    _assert_no_leftover_jinja(dst)


@pytest.mark.slow
def test_bake_without_apple_pay(tmp_path: Path):
    dst = tmp_path / "generated"
    _bake(dst, include_apple_pay=False)

    assert not (dst / "app" / "services" / "payments" / "apple_pay.py").exists()
    assert "ApplePayStoreCredentials" not in (dst / "app" / "core" / "credentials.py").read_text()
    assert "apple-services" not in (dst / "pyproject.toml").read_text()
    assert (
        "Generate dummy Apple Pay test credentials"
        not in (dst / ".github" / "workflows" / "ci.yml").read_text()
    )
    _assert_no_leftover_jinja(dst)


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
