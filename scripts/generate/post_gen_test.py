"""Unit tests for scripts/generate/post_gen.py's resolve() (feature answers -> flags).

The modules live in scripts/generate, which is not a package and is not on
pytest's pythonpath, so the directory is inserted into sys.path first.
"""

import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

import post_gen  # noqa: E402
import pytest  # noqa: E402


def answers(services="custom", include_apple_pay=False):
    return {"services": services, "include_apple_pay": include_apple_pay}


class TestResolve:
    def test_minimal_all_off(self):
        flags = post_gen.resolve(answers(services="minimal"))
        assert flags == {"_template": False, "apple_pay": False}

    def test_custom_apple_pay_on(self):
        flags = post_gen.resolve(answers(include_apple_pay=True))
        assert flags == {"_template": False, "apple_pay": True}

    def test_custom_apple_pay_off(self):
        flags = post_gen.resolve(answers(include_apple_pay=False))
        assert flags == {"_template": False, "apple_pay": False}

    def test_template_always_off(self):
        # _template is never a question; it must come back False even when
        # every real question is on.
        flags = post_gen.resolve(answers(include_apple_pay=True))
        assert flags["_template"] is False

    def test_minimal_rejects_enabled_feature(self):
        with pytest.raises(SystemExit, match="include_apple_pay=true requires services=custom"):
            post_gen.resolve(answers(services="minimal", include_apple_pay=True))

    def test_unknown_key(self):
        with pytest.raises(SystemExit, match="unknown feature answer"):
            post_gen.resolve({"services": "minimal", "include_apple_pay": False, "surprise": True})

    def test_missing_key(self):
        with pytest.raises(SystemExit, match="missing feature answer"):
            post_gen.resolve({"services": "minimal"})

    def test_non_bool_value(self):
        with pytest.raises(SystemExit, match="include_apple_pay must be a bool"):
            post_gen.resolve(answers(include_apple_pay="true"))

    def test_bad_services_value(self):
        with pytest.raises(SystemExit, match="services must be 'minimal' or 'custom'"):
            post_gen.resolve(answers(services="everything"))


class TestRuffVersion:
    def test_reads_pinned_rev(self, tmp_path, monkeypatch):
        (tmp_path / ".pre-commit-config.yaml").write_text(
            "repos:\n  - repo: https://github.com/astral-sh/ruff-pre-commit\n    rev: v0.15.22\n"
        )
        monkeypatch.chdir(tmp_path)
        assert post_gen.ruff_version() == "0.15.22"

    def test_missing_rev_raises(self, tmp_path, monkeypatch):
        (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n")
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit, match="ruff-pre-commit rev"):
            post_gen.ruff_version()

    def test_repo_config_has_a_ruff_rev(self, monkeypatch):
        # The real template config must keep a parseable pin, or every bake fails.
        monkeypatch.chdir(TEST_DIR.parent.parent)
        assert post_gen.ruff_version()


class TestNormalizePython:
    def test_skips_when_no_python_files_changed(self, monkeypatch):
        calls = []
        monkeypatch.setattr(post_gen, "run_quiet", lambda cmd, **kwargs: calls.append(cmd))
        post_gen.normalize_python([Path("README.md"), Path(".env.example")])
        assert calls == []

    def test_runs_import_sort_then_format_on_python_files(self, tmp_path, monkeypatch):
        (tmp_path / ".pre-commit-config.yaml").write_text(
            "repos:\n  - repo: https://github.com/astral-sh/ruff-pre-commit\n    rev: v0.15.22\n"
        )
        monkeypatch.chdir(tmp_path)
        calls = []
        monkeypatch.setattr(post_gen, "run_quiet", lambda cmd, **kwargs: calls.append(cmd))
        config = Path("app/core/config.py")
        post_gen.normalize_python([config, Path("README.md")])
        assert calls == [
            ["uvx", "ruff@0.15.22", "check", "--select", "I", "--fix", "--quiet", str(config)],
            ["uvx", "ruff@0.15.22", "format", "--quiet", str(config)],
        ]
