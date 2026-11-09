"""Consistency checks between the feature manifest, the repo's markers and copier.yml.

These run against the real template tree (not fixtures), so a marker typo, an
unregistered feature, a stale PATHS entry or a Copier question without a
manifest entry fails here instead of in a slow bake.
"""

import fnmatch
import itertools
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

TEST_DIR = Path(__file__).resolve().parent
REPO_ROOT = TEST_DIR.parent.parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

import features  # noqa: E402
import markers  # noqa: E402

# copier.yml questions that are about project identity, not optional features.
IDENTITY_QUESTIONS = {
    "project_name",
    "project_slug",
    "project_description",
    "author_name",
    "author_email",
    "github_username",
    "python_version",
}


def _copier_config() -> dict:
    return yaml.safe_load((REPO_ROOT / "copier.yml").read_text(encoding="utf-8"))


def _feature_questions() -> set[str]:
    return {feature.question for feature in features.FEATURES if feature.question}


def test_every_marker_names_a_manifest_feature():
    unknown = markers.used_features(REPO_ROOT) - set(features.FEATURES_BY_NAME)
    assert not unknown, f"markers or PATHS use features missing from features.py: {sorted(unknown)}"


def test_every_manifest_feature_is_used():
    used = markers.used_features(REPO_ROOT)
    unused = [f.name for f in features.FEATURES if not f.computed_from and f.name not in used]
    assert not unused, f"features.py lists features no marker or PATHS entry uses: {unused}"


def test_paths_entries_exist():
    missing = [rel for rel in features.PATHS if not (REPO_ROOT / rel).exists()]
    assert not missing, f"PATHS entries that do not exist in the template: {missing}"


def test_feature_references_are_valid():
    names = set(features.FEATURES_BY_NAME)
    for feature in features.FEATURES:
        if feature.parent is not None:
            assert feature.parent in names, f"{feature.name}: unknown parent {feature.parent!r}"
        for source in feature.computed_from:
            assert source in names, f"{feature.name}: unknown computed_from source {source!r}"
        if feature.computed_from:
            assert feature.question is None, f"{feature.name}: a computed feature must not have a question"


def test_copier_questions_match_manifest():
    questions = {key for key in _copier_config() if not key.startswith("_")}
    assert questions - IDENTITY_QUESTIONS == {"services"} | _feature_questions()


def test_feature_questions_are_gated_on_custom_services():
    config = _copier_config()
    for question in _feature_questions():
        when = str(config[question].get("when", ""))
        assert "services == 'custom'" in when, f"{question} must only be asked when services == 'custom'"
        assert config[question].get("default") is False, f"{question} must default to false"


def test_tasks_features_json_keys_match_manifest():
    task = next(task for task in _copier_config()["_tasks"] if "scripts/generate/post_gen.py" in task)
    payload = task[task.index("--features-json") + 1]
    keys = set(re.findall(r"'(\w+)'\s*:", payload))
    assert keys == {"services"} | _feature_questions()


def _copier_excluded(rel: str, patterns: list[str]) -> bool:
    """Approximate Copier's _exclude matching: a pattern matches the path or any of its parts."""
    parts = rel.split("/")
    return any(
        fnmatch.fnmatch(rel, pattern) or any(fnmatch.fnmatch(part, pattern) for part in parts) for pattern in patterns
    )


@pytest.fixture(scope="module")
def tracked_files() -> list[str]:
    """The files Copier would copy into a generated project (tracked + untracked, minus _exclude)."""
    output = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    patterns = _copier_config()["_exclude"]
    return [
        line
        for line in output.splitlines()
        if line and (REPO_ROOT / line).is_file() and not _copier_excluded(line, patterns)
    ]


def _marker_feature_names(text: str) -> set[str]:
    """Feature names used in a file's FEATURE[...] marker expressions."""
    return {name for expr in re.findall(r"FEATURE\[([^\]]+)\]", text) for name in re.split(r"[|&!]", expr) if name}


def _owning_paths(rel: str) -> list[str]:
    """PATHS entries that cover rel: the file itself or a folder above it."""
    return [key for key in features.PATHS if key == rel or (key.endswith("/") and rel.startswith(key))]


def test_every_marked_file_strips_for_every_combination_of_its_features(tracked_files):
    """The marker pass succeeds (no MarkerError) for every answer set.

    A file's markers can only fail on the features that file mentions (its
    marker expressions and the PATHS entries that own it), so trying every
    combination of those per file covers every answer set without copying the
    whole template for each one. Whole-tree runs of the CI variants are in
    check_variants_test.py.
    """
    names_all = [feature.name for feature in features.FEATURES]
    checked = 0
    for rel in tracked_files:
        path = REPO_ROOT / rel
        if markers._is_excluded(rel, features.SCAN_EXCLUDE):
            continue
        style = markers.style_for(path)
        if style is None:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        owners = _owning_paths(rel)
        names = _marker_feature_names(text)
        if not names:
            continue
        for key in owners:
            names |= _marker_feature_names(f"FEATURE[{features.PATHS[key]}]")
        names = sorted(names)
        for values in itertools.product([False, True], repeat=len(names)):
            flags = dict.fromkeys(names_all, False)
            flags.update(zip(names, values))
            if any(not markers._eval_expr(features.PATHS[key], flags, False, key, 0) for key in owners):
                continue  # the file is deleted for this answer set, never processed
            markers.process_text(text, flags, style, rel)
        checked += 1
    assert checked > 0, "no marked files found"


def test_engine_runs_on_the_whole_template_for_minimal_and_everything(tracked_files, tmp_path):
    """One whole-tree run each with every feature off and every feature on (PATHS, near-miss scan)."""
    for flags in (
        {feature.name: False for feature in features.FEATURES},
        {feature.name: feature.name != "_template" for feature in features.FEATURES},
    ):
        root = tmp_path / str(len(list(tmp_path.iterdir())))
        for rel in tracked_files:
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / rel, dst)
        markers.apply(root, flags)
