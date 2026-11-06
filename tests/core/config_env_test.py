"""Every required setting has an entry in .env.example and reaches the backend container.

A required `Settings` field (no default) that is missing from `.env.example`
breaks `cp .env.example .env`, and one missing from the backend service's
`environment:` list in docker-compose.yml breaks `docker compose up`, since
the container then cannot build its settings.
"""

import re
from pathlib import Path

import pytest

from app.core.config import Settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_ENV_NAMES = sorted(name.upper() for name, field in Settings.model_fields.items() if field.is_required())


def env_example_names() -> set[str]:
    text = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    return set(re.findall(r"^([A-Z][A-Z0-9_]*)=", text, re.MULTILINE))


def compose_backend_environment() -> set[str]:
    """Variable names in the backend service's `environment:` list (`- NAME` or `- NAME=value`)."""
    lines = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8").splitlines()
    names: set[str] = set()
    in_backend = in_environment = False
    for line in lines:
        if re.match(r"^  \S", line):  # a service key under `services:`
            in_backend = line.strip() == "backend:"
            in_environment = False
            continue
        if not in_backend:
            continue
        if re.match(r"^    \S", line):  # a key of the backend service
            in_environment = line.strip() == "environment:"
            continue
        match = re.match(r"^\s+- ([A-Z][A-Z0-9_]*)(=.*)?$", line)
        if in_environment and match:
            names.add(match.group(1))
    return names


def test_there_are_required_settings():
    assert REQUIRED_ENV_NAMES


def test_compose_backend_environment_is_parsed():
    assert "POSTGRES_HOST" in compose_backend_environment()


@pytest.mark.parametrize("name", REQUIRED_ENV_NAMES)
def test_required_setting_is_in_env_example(name):
    assert name in env_example_names(), f"{name} is required by Settings but missing from .env.example"


@pytest.mark.parametrize("name", REQUIRED_ENV_NAMES)
def test_required_setting_reaches_backend_container(name):
    assert name in compose_backend_environment(), (
        f"{name} is required by Settings but not passed to the backend service in docker-compose.yml"
    )
