"""Unit tests for scripts/generate/post_gen.py's resolve() (feature answers -> flags).

The modules live in scripts/generate, which is not a package and is not on
pytest's pythonpath, so the directory is inserted into sys.path first.
"""

import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

import features  # noqa: E402
import post_gen  # noqa: E402
import pytest  # noqa: E402

QUESTIONS = {feature.question: feature.name for feature in features.FEATURES if feature.question}


def answers(services="custom", **enabled):
    """Copier answers with every question False except the ones passed as True."""
    raw = {"services": services}
    raw.update({question: False for question in QUESTIONS})
    raw.update(enabled)
    return raw


def flags(*on):
    """Expected resolve() result: every feature False except `on`."""
    result = {feature.name: False for feature in features.FEATURES}
    result.update({name: True for name in on})
    return result


class TestResolve:
    def test_minimal_all_off(self):
        assert post_gen.resolve(answers(services="minimal")) == flags()

    def test_custom_with_nothing_chosen_is_all_off(self):
        assert post_gen.resolve(answers()) == flags()

    def test_custom_apple_pay_on(self):
        assert post_gen.resolve(answers(include_apple_pay=True)) == flags("apple_pay")

    def test_custom_backblaze_on(self):
        assert post_gen.resolve(answers(include_backblaze=True)) == flags("backblaze")

    def test_each_question_switches_only_its_feature(self):
        # A child feature (e.g. firestore) needs its parent switched on too.
        for question, name in QUESTIONS.items():
            chain = [name]
            while features.FEATURES_BY_NAME[chain[-1]].parent:
                chain.append(features.FEATURES_BY_NAME[chain[-1]].parent)
            enabled = {features.FEATURES_BY_NAME[n].question: True for n in chain}
            # Computed features (e.g. redis) follow from what is switched on.
            computed = [f.name for f in features.FEATURES if f.computed_from and set(f.computed_from) & set(chain)]
            assert post_gen.resolve(answers(**enabled)) == flags(*chain, *computed)

    def test_redis_is_computed_from_its_services(self):
        for question in (
            "include_redis_cache",
            "include_redis_rate_limit",
            "include_redis_token_blacklist",
            "include_celery",
        ):
            assert post_gen.resolve(answers(**{question: True}))["redis"] is True
        assert post_gen.resolve(answers())["redis"] is False
        assert post_gen.resolve(answers(include_gcs=True))["redis"] is False

    def test_child_without_parent_is_rejected(self):
        with pytest.raises(SystemExit, match="requires its parent feature 'firebase'"):
            post_gen.resolve(answers(include_firestore=True))

    def test_template_always_off(self):
        # _template is never a question; it must come back False even when
        # every real question is on.
        everything = answers(**{question: True for question in QUESTIONS})
        assert post_gen.resolve(everything)["_template"] is False

    def test_minimal_rejects_enabled_feature(self):
        with pytest.raises(SystemExit, match="include_apple_pay=true requires services=custom"):
            post_gen.resolve(answers(services="minimal", include_apple_pay=True))

    def test_unknown_key(self):
        with pytest.raises(SystemExit, match="unknown feature answer"):
            post_gen.resolve({**answers(services="minimal"), "surprise": True})

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
            ["uvx", "ruff@0.15.22", "check", "--select", "I", "--fix", "--no-cache", "--quiet", str(config)],
            ["uvx", "ruff@0.15.22", "format", "--no-cache", "--quiet", str(config)],
        ]


class TestDetectSecretsConfig:
    def test_repo_config_has_a_detect_secrets_rev(self, monkeypatch):
        monkeypatch.chdir(TEST_DIR.parent.parent)
        assert post_gen.hook_rev("Yelp/detect-secrets")

    def test_repo_exclude_matches_pre_commit_hook(self, monkeypatch):
        monkeypatch.chdir(TEST_DIR.parent.parent)
        exclude = post_gen.detect_secrets_exclude()
        assert exclude.search("uv.lock")
        assert exclude.search("docs/architecture/overview.html")
        assert not exclude.search("app/main.py")
        assert not exclude.search("tests/conftest.py")

    def test_exclude_is_read_from_the_hook_block_only(self, tmp_path, monkeypatch):
        (tmp_path / ".pre-commit-config.yaml").write_text(
            "repos:\n"
            "  - repo: https://github.com/Yelp/detect-secrets\n"
            "    rev: v1.5.0\n"
            "    hooks:\n"
            "      - id: detect-secrets\n"
            "        args: [--baseline, .secrets.baseline]\n"
            "  - repo: other\n"
            "    hooks:\n"
            "      - id: other\n"
            "        exclude: ^app/\n"
        )
        monkeypatch.chdir(tmp_path)
        assert not post_gen.detect_secrets_exclude().search("app/main.py")

    def test_missing_hook_raises(self, tmp_path, monkeypatch):
        (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n")
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit, match="detect-secrets hook"):
            post_gen.detect_secrets_exclude()


class TestRefreshSecretsBaseline:
    @pytest.fixture
    def project(self, tmp_path, monkeypatch):
        (tmp_path / ".pre-commit-config.yaml").write_text(
            "repos:\n"
            "  - repo: https://github.com/Yelp/detect-secrets\n"
            "    rev: v1.5.0\n"
            "    hooks:\n"
            "      - id: detect-secrets\n"
            "        exclude: ^uv\\.lock$\n"
        )
        (tmp_path / ".secrets.baseline").write_text("{}\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("FASTAPI_TEMPLATE_STRICT", raising=False)
        listed = subprocess_result(0, "app/main.py\nuv.lock\ntests/conftest.py\n")
        monkeypatch.setattr(post_gen, "run_quiet", lambda cmd, **kwargs: listed)
        return tmp_path

    def _hook(self, monkeypatch, returncode):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return subprocess_result(returncode, "")

        monkeypatch.setattr(post_gen.subprocess, "run", fake_run)
        return calls

    def test_runs_pinned_hook_on_listed_files_minus_exclude(self, project, monkeypatch):
        calls = self._hook(monkeypatch, 3)
        post_gen.refresh_secrets_baseline()
        assert calls == [
            [
                "uvx",
                "--from",
                "detect-secrets==1.5.0",
                "detect-secrets-hook",
                "--baseline",
                ".secrets.baseline",
                "app/main.py",
                "tests/conftest.py",
            ]
        ]

    def test_skips_without_a_baseline(self, project, monkeypatch):
        (project / ".secrets.baseline").unlink()
        calls = self._hook(monkeypatch, 0)
        post_gen.refresh_secrets_baseline()
        assert calls == []

    def test_new_secret_warns(self, project, monkeypatch, capsys):
        self._hook(monkeypatch, 1)
        post_gen.refresh_secrets_baseline()
        assert "could not refresh .secrets.baseline" in capsys.readouterr().out

    def test_new_secret_is_fatal_in_strict_mode(self, project, monkeypatch):
        self._hook(monkeypatch, 1)
        monkeypatch.setenv("FASTAPI_TEMPLATE_STRICT", "1")
        with pytest.raises(SystemExit, match="exit code 1"):
            post_gen.refresh_secrets_baseline()


def subprocess_result(returncode, stdout):
    return post_gen.subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")
