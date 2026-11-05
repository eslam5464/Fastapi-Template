"""Tests for scripts/generate/check_variants.py.

The parametrized test runs the real offline pipeline for every variant, so it
is the quickest end-to-end check that markers, PATHS and imports agree.
"""

import sys
from pathlib import Path

import pytest

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

import check_variants  # noqa: E402
import variants  # noqa: E402


@pytest.fixture(scope="module")
def files():
    return check_variants.template_files()


@pytest.mark.parametrize("name", list(variants.all_variants()))
def test_variant_is_clean(name, files):
    problems = check_variants.check_variant(name, variants.all_variants()[name], files)
    assert problems == [], "\n".join(problems)


def _tree(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


MINIMAL = variants.answers(set())


def test_reports_missing_first_party_module(tmp_path):
    root = _tree(tmp_path, {"app/__init__.py": "", "app/main.py": "from app.gone import x\n"})
    problems = check_variants.check_tree(root, MINIMAL)
    assert any("imports app.gone, which this variant does not ship" in p for p in problems)


def test_reports_disallowed_third_party_import(tmp_path):
    root = _tree(tmp_path, {"app/__init__.py": "", "app/pay.py": "import appstoreserverlibrary\n"})
    problems = check_variants.check_tree(root, MINIMAL)
    assert any("'appstoreserverlibrary', not allowed" in p for p in problems)


def test_test_only_import_rejected_in_app(tmp_path):
    root = _tree(tmp_path, {"app/__init__.py": "", "app/x.py": "import pytest\n"})
    problems = check_variants.check_tree(root, MINIMAL)
    assert any("'pytest', not allowed" in p for p in problems)


def test_test_only_import_allowed_in_tests(tmp_path):
    root = _tree(tmp_path, {"tests/x_test.py": "import pytest\n\npytest.skip\n"})
    assert check_variants.check_tree(root, MINIMAL) == []


def test_reports_forbidden_token_of_disabled_feature(tmp_path):
    root = _tree(tmp_path, {"app/x.py": "NAME = 'ApplePay'\n"})
    problems = check_variants.check_tree(root, MINIMAL)
    assert any("of a disabled feature" in p for p in problems)


def test_reports_syntax_error(tmp_path):
    root = _tree(tmp_path, {"app/x.py": "def (:\n"})
    problems = check_variants.check_tree(root, MINIMAL)
    assert any("does not parse" in p for p in problems)


def test_reports_invalid_toml(tmp_path):
    root = _tree(tmp_path, {"pyproject.toml": "[tool\n"})
    problems = check_variants.check_tree(root, MINIMAL)
    assert any("invalid TOML" in p for p in problems)
