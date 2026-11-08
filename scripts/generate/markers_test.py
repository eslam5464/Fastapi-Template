"""Unit tests for scripts/generate/markers.py (feature marker engine).

The modules live in scripts/generate, which is not a package and is not on
pytest's pythonpath, so the directory is inserted into sys.path first.
"""

from __future__ import annotations

import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

import features  # noqa: E402
import markers  # noqa: E402
import pytest  # noqa: E402

FLAGS = {"a": True, "b": False, "c": True, "_template": False}


def pro(text, flags=None, style="hash", path="f.py"):
    return markers.process_text(text, flags if flags is not None else FLAGS, style, path)


def w(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def r(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def fake_manifest(monkeypatch, paths=None, scan_exclude=()):
    monkeypatch.setattr(features, "PATHS", {} if paths is None else paths)
    monkeypatch.setattr(features, "SCAN_EXCLUDE", tuple(scan_exclude))


class TestProcessText:
    def test_kept_block_keeps_content_and_drops_markers(self):
        text = "x = 1\n# --- FEATURE[a] START ---\ny = 2\n# --- FEATURE[a] END ---\nz = 3\n"
        assert pro(text) == "x = 1\ny = 2\nz = 3\n"

    def test_removed_block(self):
        text = "x = 1\n# --- FEATURE[b] START ---\ny = 2\n# --- FEATURE[b] END ---\nz = 3\n"
        assert pro(text) == "x = 1\nz = 3\n"

    def test_nested_outer_on_inner_off(self):
        text = (
            "# --- FEATURE[a] START ---\n"
            "keep1\n"
            "# --- FEATURE[b] START ---\n"
            "drop\n"
            "# --- FEATURE[b] END ---\n"
            "keep2\n"
            "# --- FEATURE[a] END ---\n"
        )
        assert pro(text) == "keep1\nkeep2\n"

    def test_nested_outer_off_inner_on(self):
        text = (
            "head\n"
            "# --- FEATURE[b] START ---\n"
            "d1\n"
            "# --- FEATURE[a] START ---\n"
            "d2\n"
            "# --- FEATURE[a] END ---\n"
            "d3\n"
            "# --- FEATURE[b] END ---\n"
            "tail\n"
        )
        assert pro(text) == "head\ntail\n"

    def test_inner_marker_validated_even_when_outer_off(self):
        text = (
            "# --- FEATURE[b] START ---\n"
            "# --- FEATURE[zzz] START ---\n"
            "# --- FEATURE[zzz] END ---\n"
            "# --- FEATURE[b] END ---\n"
            "tail\n"
        )
        with pytest.raises(markers.MarkerError, match="unknown feature 'zzz'"):
            pro(text)

    @pytest.mark.parametrize(
        ("flags", "inner"),
        [
            ({"a": True, "b": True}, "inner\n"),
            ({"a": True, "b": False}, "inner\n"),
            ({"a": False, "b": True}, "inner\n"),
            ({"a": False, "b": False}, ""),
        ],
    )
    def test_or_truth_table(self, flags, inner):
        text = "head\n# --- FEATURE[a|b] START ---\ninner\n# --- FEATURE[a|b] END ---\ntail\n"
        assert pro(text, flags) == f"head\n{inner}tail\n"

    @pytest.mark.parametrize(
        ("flags", "inner"),
        [
            ({"a": True, "b": True}, "inner\n"),
            ({"a": True, "b": False}, ""),
            ({"a": False, "b": True}, ""),
            ({"a": False, "b": False}, ""),
        ],
    )
    def test_and_truth_table(self, flags, inner):
        text = "head\n# --- FEATURE[a&b] START ---\ninner\n# --- FEATURE[a&b] END ---\ntail\n"
        assert pro(text, flags) == f"head\n{inner}tail\n"

    def test_negation_in_html_kept(self):
        text = "head\n<!-- --- FEATURE[!b] START --- -->\ninner\n<!-- --- FEATURE[!b] END --- -->\ntail\n"
        assert pro(text, FLAGS, "html", "f.md") == "head\ninner\ntail\n"

    def test_negation_in_html_removed(self):
        text = "head\n<!-- --- FEATURE[!a] START --- -->\ninner\n<!-- --- FEATURE[!a] END --- -->\ntail\n"
        assert pro(text, FLAGS, "html", "f.md") == "head\ntail\n"

    def test_negation_in_hash_errors(self):
        text = "# --- FEATURE[!a] START ---\ninner\n# --- FEATURE[!a] END ---\n"
        with pytest.raises(markers.MarkerError, match="only allowed in html"):
            pro(text)

    def test_leading_and_trailing_whitespace_around_marker(self):
        text = "x\n  # --- FEATURE[a] START ---  \ny\n\t# --- FEATURE[a] END ---\n"
        assert pro(text) == "x\ny\n"

    def test_html_style_blocks(self):
        kept = "intro\n<!-- --- FEATURE[a] START --- -->\nbody\n<!-- --- FEATURE[a] END --- -->\noutro\n"
        assert pro(kept, FLAGS, "html", "f.md") == "intro\nbody\noutro\n"
        gone = "intro\n<!-- --- FEATURE[b] START --- -->\nbody\n<!-- --- FEATURE[b] END --- -->\noutro\n"
        assert pro(gone, FLAGS, "html", "f.md") == "intro\noutro\n"


class TestBlankLineRule:
    def test_one_before_one_after_keeps_one(self):
        text = "x\n\n# --- FEATURE[b] START ---\ny\n# --- FEATURE[b] END ---\n\nz\n"
        assert pro(text) == "x\n\nz\n"

    def test_two_before_zero_after_keeps_two(self):
        text = "x\n\n\n# --- FEATURE[b] START ---\ny\n# --- FEATURE[b] END ---\nz\n"
        assert pro(text) == "x\n\n\nz\n"

    def test_two_before_one_after_keeps_two(self):
        text = "x\n\n\n# --- FEATURE[b] START ---\ny\n# --- FEATURE[b] END ---\n\nz\n"
        assert pro(text) == "x\n\n\nz\n"

    def test_zero_before_zero_after_keeps_zero(self):
        text = "x\n# --- FEATURE[b] START ---\ny\n# --- FEATURE[b] END ---\nz\n"
        assert pro(text) == "x\nz\n"

    def test_block_at_start_trailing_blank_inside_leaves_no_leading_blank(self):
        text = "# --- FEATURE[b] START ---\ny\n\n# --- FEATURE[b] END ---\nz\n"
        assert pro(text) == "z\n"

    def test_block_at_end_of_file(self):
        text = "x\n# --- FEATURE[b] START ---\ny\n# --- FEATURE[b] END ---\n"
        assert pro(text) == "x\n"

    def test_kept_block_marker_removal_never_adds_blank_run(self):
        text = "x\n\n# --- FEATURE[a] START ---\n\ninner\n# --- FEATURE[a] END ---\nz\n"
        assert pro(text) == "x\n\ninner\nz\n"


class TestLineEndings:
    def test_crlf_kept_block_stays_crlf(self):
        text = "x\r\n# --- FEATURE[a] START ---\r\ny\r\n# --- FEATURE[a] END ---\r\n"
        assert pro(text) == "x\r\ny\r\n"

    def test_crlf_removed_block_stays_crlf(self):
        text = "x\r\n# --- FEATURE[b] START ---\r\ny\r\n# --- FEATURE[b] END ---\r\nz\r\n"
        assert pro(text) == "x\r\nz\r\n"

    def test_crlf_blank_line_rule(self):
        text = "x\r\n\r\n# --- FEATURE[b] START ---\r\ny\r\n# --- FEATURE[b] END ---\r\n\r\nz\r\n"
        assert pro(text) == "x\r\n\r\nz\r\n"

    def test_no_marker_file_byte_identical_lf(self):
        text = "import os\n\n\ndef f():\n    pass\n\n\n"
        assert pro(text) == text

    def test_no_marker_file_byte_identical_crlf(self):
        text = "a\r\n\r\nb\r\n\r\n\r\n"
        assert pro(text) == text

    def test_no_marker_file_without_final_newline(self):
        assert pro("a\nb") == "a\nb"

    def test_empty_file_unchanged(self):
        assert pro("") == ""


class TestEvalExpr:
    @pytest.mark.parametrize(
        ("expr", "flags", "expected"),
        [
            ("a", {"a": True}, True),
            ("a", {"a": False}, False),
            ("a|b", {"a": False, "b": True}, True),
            ("a|b", {"a": False, "b": False}, False),
            ("a&b", {"a": True, "b": True}, True),
            ("a&b", {"a": True, "b": False}, False),
            ("!a", {"a": False}, True),
            ("!a", {"a": True}, False),
        ],
    )
    def test_values(self, expr, flags, expected):
        assert markers.eval_expr(expr, flags, allow_not=True) is expected

    def test_unknown_feature_raises(self):
        with pytest.raises(markers.MarkerError, match="unknown feature 'zzz'"):
            markers.eval_expr("a|zzz", {"a": True}, allow_not=False)

    def test_negation_not_allowed_without_allow_not(self):
        with pytest.raises(markers.MarkerError, match="only allowed in html"):
            markers.eval_expr("!a", {"a": True}, allow_not=False)


class TestStyleFor:
    @pytest.mark.parametrize(
        ("name", "style"),
        [
            ("x.py", "hash"),
            ("x.toml", "hash"),
            ("x.yml", "hash"),
            ("x.yaml", "hash"),
            ("x.ini", "hash"),
            ("x.cfg", "hash"),
            ("x.sh", "hash"),
            ("Dockerfile", "hash"),
            (".gitignore", "hash"),
            (".dockerignore", "hash"),
            (".env.example", "hash"),
            ("x.md", "html"),
            ("x.txt", "html"),
            ("x.html", "html"),
            ("x.json", None),
            ("x.svg", None),
            ("x.jinja", None),
            ("LICENSE", None),
        ],
    )
    def test_style_for(self, name, style):
        assert markers.style_for(Path(name)) == style


class TestErrors:
    def test_error_str_and_attributes(self):
        err = markers.MarkerError("f.py", 3, "boom")
        assert str(err) == "f.py:3: boom"
        assert (err.path, err.line_no, err.message) == ("f.py", 3, "boom")

    def test_unknown_feature(self):
        text = "x\n# --- FEATURE[zzz] START ---\ny\n# --- FEATURE[zzz] END ---\n"
        with pytest.raises(markers.MarkerError, match="unknown feature 'zzz'"):
            pro(text)

    @pytest.mark.parametrize(
        "expr",
        ["a |b", "a| b", "a|(b)", "a|b&c", "a.b", "!", "!a|b"],
    )
    def test_malformed_expressions(self, expr):
        text = f"# --- FEATURE[{expr}] START ---\ny\n# --- FEATURE[{expr}] END ---\n"
        with pytest.raises(markers.MarkerError):
            pro(text, {"a": True, "b": True})

    def test_end_without_start(self):
        with pytest.raises(markers.MarkerError, match="END marker without a matching START"):
            pro("x\n# --- FEATURE[a] END ---\n")

    def test_unclosed_start_at_eof(self):
        with pytest.raises(markers.MarkerError, match="unclosed START marker"):
            pro("x\n# --- FEATURE[a] START ---\ny\n")

    def test_end_expression_mismatch(self):
        text = "# --- FEATURE[a] START ---\ny\n# --- FEATURE[b] END ---\n"
        with pytest.raises(markers.MarkerError, match="does not match START expression"):
            pro(text)

    def test_end_expression_text_must_match_exactly(self):
        text = "# --- FEATURE[a|b] START ---\ny\n# --- FEATURE[b|a] END ---\n"
        with pytest.raises(markers.MarkerError, match="does not match START expression"):
            pro(text, {"a": True, "b": True})

    @pytest.mark.parametrize(
        "line",
        [
            "# --- APPLE_PAY_SETTINGS_START ---",
            "# --- APPLE_PAY_SETTINGS_END ---",
            "<!-- TEMPLATE_SECTION_START -->",
            "<!-- TEMPLATE_SECTION_END -->",
            "# FEATURE[a] START ---",
            "# --- FEATURE[a] MIDDLE ---",
            "# --- FEATURE[] START ---",
        ],
    )
    def test_near_miss_hash(self, line):
        with pytest.raises(markers.MarkerError, match="near-miss"):
            pro(f"x\n{line}\n")

    def test_near_miss_old_style_in_html(self):
        with pytest.raises(markers.MarkerError, match="near-miss"):
            pro("x\n<!-- TEMPLATE_SECTION_START -->\n", FLAGS, "html", "f.md")

    def test_html_marker_in_hash_file_is_near_miss(self):
        text = "x\n<!-- --- FEATURE[a] START --- -->\n"
        with pytest.raises(markers.MarkerError, match="near-miss"):
            pro(text)

    def test_result_empty_raises(self):
        with pytest.raises(markers.MarkerError, match="empty or whitespace-only"):
            pro("# --- FEATURE[b] START ---\ny\n# --- FEATURE[b] END ---\n")

    def test_result_whitespace_only_raises(self):
        text = "  \n# --- FEATURE[b] START ---\n# --- FEATURE[b] END ---\n"
        with pytest.raises(markers.MarkerError, match="empty or whitespace-only"):
            pro(text)

    def test_invalid_style_raises(self):
        with pytest.raises(ValueError, match="invalid style"):
            pro("x\n", FLAGS, "json")


class TestApply:
    def test_processes_files_and_leaves_unmarked_alone(self, tmp_path, monkeypatch):
        fake_manifest(monkeypatch)
        w(tmp_path / "on.py", "head\n# --- FEATURE[a] START ---\nkeep\n# --- FEATURE[a] END ---\ntail\n")
        w(tmp_path / "off.py", "head\n# --- FEATURE[b] START ---\ndrop\n# --- FEATURE[b] END ---\ntail\n")
        w(tmp_path / "plain.md", "no markers\n")
        w(tmp_path / "data.json", '{"a": 1}\n')
        markers.apply(tmp_path, FLAGS)
        assert r(tmp_path / "on.py") == "head\nkeep\ntail\n"
        assert r(tmp_path / "off.py") == "head\ntail\n"
        assert r(tmp_path / "plain.md") == "no markers\n"
        assert r(tmp_path / "data.json") == '{"a": 1}\n'

    def test_returns_only_rewritten_files(self, tmp_path, monkeypatch):
        fake_manifest(monkeypatch)
        w(tmp_path / "on.py", "head\n# --- FEATURE[a] START ---\nkeep\n# --- FEATURE[a] END ---\ntail\n")
        w(tmp_path / "plain.py", "x = 1\n")
        changed = markers.apply(tmp_path, FLAGS)
        assert changed == [tmp_path / "on.py"]

    def test_paths_deletion_of_file_and_directory(self, tmp_path, monkeypatch):
        fake_manifest(monkeypatch, paths={"extras/": "b", "extra.txt": "b", "keeper.py": "a"})
        extras = tmp_path / "extras"
        extras.mkdir()
        w(extras / "x.py", "x = 1\n")
        w(tmp_path / "extra.txt", "bye\n")
        w(tmp_path / "keeper.py", "x = 1\n")
        markers.apply(tmp_path, FLAGS)
        assert not extras.exists()
        assert not (tmp_path / "extra.txt").exists()
        assert (tmp_path / "keeper.py").exists()

    def test_paths_deletion_removes_folders_it_empties(self, tmp_path, monkeypatch):
        fake_manifest(monkeypatch, paths={"docs/integrations/b.md": "b", "docs/other/b.md": "b"})
        (tmp_path / "docs" / "integrations").mkdir(parents=True)
        (tmp_path / "docs" / "other").mkdir()
        w(tmp_path / "docs" / "integrations" / "b.md", "b\n")
        w(tmp_path / "docs" / "other" / "b.md", "b\n")
        w(tmp_path / "docs" / "other" / "keep.md", "keep\n")
        w(tmp_path / "docs" / "index.md", "index\n")
        markers.apply(tmp_path, FLAGS)
        assert not (tmp_path / "docs" / "integrations").exists()
        assert (tmp_path / "docs" / "other" / "keep.md").exists()
        assert (tmp_path / "docs" / "index.md").exists()

    def test_paths_file_inside_deleted_directory(self, tmp_path, monkeypatch):
        # A child feature's file inside its parent's folder: both off.
        fake_manifest(monkeypatch, paths={"pkg/": "b", "pkg/child.py": "b"})
        (tmp_path / "pkg").mkdir()
        w(tmp_path / "pkg" / "child.py", "x = 1\n")
        w(tmp_path / "pkg" / "base.py", "x = 1\n")
        markers.apply(tmp_path, FLAGS)
        assert not (tmp_path / "pkg").exists()

    def test_paths_file_inside_kept_directory(self, tmp_path, monkeypatch):
        fake_manifest(monkeypatch, paths={"pkg/": "a", "pkg/child.py": "b"})
        (tmp_path / "pkg").mkdir()
        w(tmp_path / "pkg" / "child.py", "x = 1\n")
        w(tmp_path / "pkg" / "base.py", "x = 1\n")
        markers.apply(tmp_path, FLAGS)
        assert (tmp_path / "pkg" / "base.py").exists()
        assert not (tmp_path / "pkg" / "child.py").exists()

    def test_paths_deletion_never_removes_root(self, tmp_path, monkeypatch):
        fake_manifest(monkeypatch, paths={"only.py": "b"})
        w(tmp_path / "only.py", "x = 1\n")
        markers.apply(tmp_path, FLAGS)
        assert tmp_path.is_dir()

    def test_paths_entry_kept_when_expression_true(self, tmp_path, monkeypatch):
        fake_manifest(monkeypatch, paths={"keeper.py": "a"})
        w(tmp_path / "keeper.py", "x = 1\n")
        markers.apply(tmp_path, FLAGS)
        assert r(tmp_path / "keeper.py") == "x = 1\n"

    def test_missing_paths_entry_raises(self, tmp_path, monkeypatch):
        fake_manifest(monkeypatch, paths={"gone.py": "a"})
        with pytest.raises(markers.MarkerError, match="does not exist under root"):
            markers.apply(tmp_path, FLAGS)

    def test_paths_expression_unknown_feature_raises(self, tmp_path, monkeypatch):
        fake_manifest(monkeypatch, paths={"keeper.py": "a"})
        w(tmp_path / "keeper.py", "x = 1\n")
        with pytest.raises(markers.MarkerError, match="unknown feature"):
            markers.apply(tmp_path, {"b": False})

    def test_scan_exclude_skipped(self, tmp_path, monkeypatch):
        fake_manifest(monkeypatch, scan_exclude=(".git/", "skipme.txt"))
        w(tmp_path / "ok.py", "x = 1\n")
        git = tmp_path / ".git"
        git.mkdir()
        w(git / "old.py", "# --- APPLE_PAY_START ---\n")
        w(tmp_path / "skipme.txt", "# --- FEATURE[a] START ---\n")
        markers.apply(tmp_path, FLAGS)
        assert r(tmp_path / "ok.py") == "x = 1\n"
        assert r(tmp_path / "skipme.txt") == "# --- FEATURE[a] START ---\n"
        assert r(git / "old.py") == "# --- APPLE_PAY_START ---\n"

    def test_binary_files_skipped(self, tmp_path, monkeypatch):
        fake_manifest(monkeypatch)
        invalid = tmp_path / "invalid.py"
        invalid.write_bytes(b"\xff\xfe\xfa")
        nul = tmp_path / "nul.py"
        nul.write_bytes(b"x = 1\n\x00\n")
        markers.apply(tmp_path, FLAGS)
        assert invalid.read_bytes() == b"\xff\xfe\xfa"
        assert nul.read_bytes() == b"x = 1\n\x00\n"

    def test_marker_in_unsupported_file_type_raises(self, tmp_path, monkeypatch):
        fake_manifest(monkeypatch)
        w(tmp_path / "data.json", '{\n  "x": "# --- FEATURE[a] START ---"\n}\n')
        with pytest.raises(markers.MarkerError, match="unsupported file type"):
            markers.apply(tmp_path, FLAGS)

    def test_idempotent_second_apply_changes_nothing(self, tmp_path, monkeypatch):
        fake_manifest(monkeypatch)
        w(tmp_path / "m.py", "x = 1\n\n# --- FEATURE[b] START ---\ny = 2\n# --- FEATURE[b] END ---\n\nz = 3\n")
        w(tmp_path / "n.md", "intro\n<!-- --- FEATURE[a] START --- -->\nbody\n<!-- --- FEATURE[a] END --- -->\n")
        markers.apply(tmp_path, FLAGS)
        snap = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
        markers.apply(tmp_path, FLAGS)
        snap2 = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
        assert snap == snap2
        assert r(tmp_path / "m.py") == "x = 1\n\nz = 3\n"
        assert r(tmp_path / "n.md") == "intro\nbody\n"


class TestUsedFeatures:
    def test_used_features_from_markers_and_paths(self, tmp_path, monkeypatch):
        fake_manifest(monkeypatch, paths={"pay/": "a", "note.txt": "c"})
        pay = tmp_path / "pay"
        pay.mkdir()
        w(pay / "p.py", "# --- FEATURE[a] START ---\nx\n# --- FEATURE[a] END ---\n")
        w(tmp_path / "m.py", "# --- FEATURE[a|b] START ---\nx\n# --- FEATURE[a|b] END ---\n")
        w(tmp_path / "d.md", "<!-- --- FEATURE[!c] START --- -->\nx\n<!-- --- FEATURE[!c] END --- -->\n")
        w(tmp_path / "note.txt", "hello\n")
        assert markers.used_features(tmp_path) == {"a", "b", "c"}

    def test_used_features_skips_scan_exclude(self, tmp_path, monkeypatch):
        fake_manifest(monkeypatch, scan_exclude=("skip.py",))
        w(tmp_path / "skip.py", "# --- FEATURE[b] START ---\nx\n# --- FEATURE[b] END ---\n")
        w(tmp_path / "m.py", "# --- FEATURE[a] START ---\nx\n# --- FEATURE[a] END ---\n")
        assert markers.used_features(tmp_path) == {"a"}


class TestManifest:
    def test_manifest_features_and_paths_exist(self):
        assert features.FEATURES_BY_NAME["_template"].question is None
        assert features.FEATURES_BY_NAME["apple_pay"].question == "include_apple_pay"
        for rel in features.PATHS:
            assert (Path(__file__).resolve().parent.parent.parent / rel).exists(), rel
