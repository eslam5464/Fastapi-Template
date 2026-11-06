"""Tests for scripts/generate/ci_checks.py."""

import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

import ci_checks  # noqa: E402
import pytest  # noqa: E402


def _tree(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def test_app_modules_skip_alembic(tmp_path):
    root = _tree(
        tmp_path,
        {
            "app/__init__.py": "",
            "app/core/__init__.py": "",
            "app/core/config.py": "",
            "app/alembic/env.py": "raise RuntimeError('runs a migration')\n",
        },
    )
    assert ci_checks.app_modules(root) == ["app.core", "app.core.config"]


@pytest.fixture
def isolated_app_package(monkeypatch):
    """Import a throwaway `app` package, then restore sys.path and sys.modules."""
    monkeypatch.setattr(sys, "path", list(sys.path))
    saved = {name: module for name, module in sys.modules.items() if name == "app" or name.startswith("app.")}
    for name in saved:
        del sys.modules[name]
    yield
    for name in [name for name in sys.modules if name == "app" or name.startswith("app.")]:
        del sys.modules[name]
    sys.modules.update(saved)


def test_import_app_reports_every_broken_module(tmp_path, isolated_app_package, capsys):
    root = _tree(
        tmp_path,
        {
            "app/__init__.py": "",
            "app/good.py": "",
            "app/bad_one.py": "import not_installed_package_one\n",
            "app/bad_two.py": "import not_installed_package_two\n",
        },
    )
    assert ci_checks.import_app(root) == 1
    out = capsys.readouterr().out
    assert "app.bad_one: ModuleNotFoundError" in out
    assert "app.bad_two: ModuleNotFoundError" in out
    assert "imported 1/3 app modules" in out


def test_import_app_only_warns_on_configuration_errors(tmp_path, isolated_app_package, capsys):
    root = _tree(
        tmp_path,
        {
            "app/__init__.py": "",
            "app/needs_creds.py": "import json\n\nraise RuntimeError('Invalid credentials')\n",
        },
    )
    assert ci_checks.import_app(root) == 0
    assert "WARN app.needs_creds: RuntimeError: Invalid credentials" in capsys.readouterr().out


def test_import_app_passes_clean_package(tmp_path, isolated_app_package):
    root = _tree(tmp_path, {"app/__init__.py": "", "app/good.py": "VALUE = 1\n"})
    assert ci_checks.import_app(root) == 0


JUNIT = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" skipped="1" tests="2">
<testcase classname="tests.a_test" name="test_runs" time="0.1" />
<testcase classname="tests.b_test" name="test_skipped" time="0.0">
<skipped type="pytest.skip" message="needs an optional SDK">tests/b_test.py:3</skipped>
</testcase>
</testsuite></testsuites>
"""


def test_no_skips_fails_and_lists_skipped_tests(tmp_path, capsys):
    report = tmp_path / "junit.xml"
    report.write_text(JUNIT, encoding="utf-8")
    assert ci_checks.no_skips(report) == 1
    assert "SKIPPED tests.b_test::test_skipped - needs an optional SDK" in capsys.readouterr().out


def test_no_skips_passes_clean_report(tmp_path):
    report = tmp_path / "junit.xml"
    report.write_text(
        '<testsuites><testsuite><testcase classname="tests.a_test" name="test_runs" /></testsuite></testsuites>',
        encoding="utf-8",
    )
    assert ci_checks.no_skips(report) == 0
