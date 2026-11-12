"""Render copier.yml's Jinja defaults directly to lock the --defaults behaviour.

These are fast and never bake, so a wrong default string here is caught without
a slow Copier run.
"""

from pathlib import Path

import pytest
import yaml

jinja2 = pytest.importorskip("jinja2")

TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent.parent

_COPIER_CONFIG = yaml.safe_load((REPO_ROOT / "copier.yml").read_text(encoding="utf-8"))


def _render(template: str, **context) -> str:
    return jinja2.Template(template).render(**context)


def test_services_default_is_full_under_defaults():
    rendered = _render(_COPIER_CONFIG["services"]["default"], _copier_conf={"defaults": True})
    assert rendered == "full"


def test_services_default_is_minimal_without_defaults():
    rendered = _render(_COPIER_CONFIG["services"]["default"], _copier_conf={"defaults": False})
    assert rendered == "minimal"


def test_include_default_follows_full_services():
    for value, expected in (("full", "True"), ("custom", "False"), ("minimal", "False")):
        rendered = _render(_COPIER_CONFIG["include_auth"]["default"], services=value)
        assert rendered == expected, f"services={value!r}"
