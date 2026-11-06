"""Unit tests for scripts/generate/variants.py (variants derived from the manifest)."""

import sys
from pathlib import Path

import pytest

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

import bake  # noqa: E402
import features  # noqa: E402
import post_gen  # noqa: E402
import variants  # noqa: E402


@pytest.fixture
def fake_manifest(monkeypatch):
    """a, b (child of a), c - plus the reserved _template."""
    fake = (
        features.Feature("_template"),
        features.Feature("a", question="include_a"),
        features.Feature("b", question="include_b", parent="a"),
        features.Feature("c", question="include_c"),
    )
    monkeypatch.setattr(features, "FEATURES", fake)
    monkeypatch.setattr(features, "FEATURES_BY_NAME", {f.name: f for f in fake})


def _enabled(raw):
    return {key for key, value in raw.items() if key != "services" and value}


def test_fake_graph_variants(fake_manifest):
    found = {name: _enabled(raw) for name, raw in variants.all_variants().items()}
    assert found == {
        "minimal": set(),
        "full": {"include_a", "include_b", "include_c"},
        "only-a": {"include_a"},
        "only-b": {"include_a", "include_b"},  # b needs its parent a
        "only-c": {"include_c"},
        "without-b": {"include_a", "include_c"},
        # without-a drops a and its child b, leaving {c} == only-c, and
        # without-c == {a, b} == only-b: duplicates are listed once.
    }


def test_services_value(fake_manifest):
    all_variants = variants.all_variants()
    assert all_variants["minimal"]["services"] == "minimal"
    assert all(raw["services"] == "custom" for name, raw in all_variants.items() if name != "minimal")


def test_every_variant_resolves(fake_manifest):
    for raw in variants.all_variants().values():
        post_gen.resolve(raw)  # raises SystemExit on an invalid answer set


def test_answers_rejects_unknown_feature(fake_manifest):
    with pytest.raises(ValueError, match="not switchable"):
        variants.answers({"_template"})


def test_copier_data_args(fake_manifest):
    assert variants.copier_data_args(variants.answers(set())) == []
    assert variants.copier_data_args(variants.answers({"a", "b"})) == [
        "--data",
        "services=custom",
        "--data",
        "include_a=true",
        "--data",
        "include_b=true",
    ]


def test_matrix_shape(fake_manifest):
    entries = variants.matrix()["include"]
    assert [entry["variant"] for entry in entries] == list(variants.all_variants())
    minimal = entries[0]
    assert minimal == {"variant": "minimal", "data": "", "features": ""}
    only_b = next(entry for entry in entries if entry["variant"] == "only-b")
    assert only_b["features"] == "a,b"
    assert only_b["data"] == "--data services=custom --data include_a=true --data include_b=true"


def test_real_manifest_variants():
    names = list(variants.all_variants())
    assert names[:2] == ["minimal", "full"]
    for feature in variants.question_features():
        # Every switchable feature gets a bake with it alone (plus its parents).
        assert f"only-{feature.name}" in names
    for name, raw in variants.all_variants().items():
        assert variants.enabled_features(raw) or name == "minimal"


def test_bake_command_for_known_variant(tmp_path):
    cmd = bake.copier_command("full", tmp_path / "out", "HEAD")
    assert cmd[1:4] == ["-m", "copier", "copy"]
    assert "--defaults" in cmd and "--trust" in cmd
    assert "include_apple_pay=true" in cmd


def test_bake_rejects_unknown_variant(tmp_path):
    with pytest.raises(SystemExit, match="unknown variant"):
        bake.copier_command("nope", tmp_path, "HEAD")
