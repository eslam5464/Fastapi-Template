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
        assert config[question].get("default") == "{{ services == 'full' }}", (
            f"{question} must default to the full-service expression"
        )


def test_services_choices_and_default():
    config = _copier_config()
    services = config["services"]
    assert [choice for label, choice in services["choices"].items()] == ["minimal", "custom", "full"]
    assert services["default"] == "{{ 'full' if _copier_conf.defaults else 'minimal' }}"


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


def _expr_feature_names(expr: str) -> set[str]:
    """Feature names referenced in one marker expression."""
    return {name for name in re.split(r"[|&!]", expr) if name}


def _content_line_enclosures(text: str, style: str) -> tuple[bool, list[list[str]]]:
    """Walk a file's lines the way process_text does.

    Returns whether any non-blank, non-marker line sits outside every marker
    block, and the enclosing START expressions of each such line.
    """
    marker_re = markers._MARKER_RE[style]
    has_outside = False
    enclosures: list[list[str]] = []
    stack: list[str] = []
    for line in text.splitlines(keepends=True):
        body = markers._body(line)
        match = marker_re.fullmatch(body)
        if match is None:
            if body.strip() != "":
                if not stack:
                    has_outside = True
                enclosures.append(list(stack))
            continue
        if match.group("side") == "START":
            stack.append(match.group("expr"))
        elif stack:
            stack.pop()
    return has_outside, enclosures


def test_every_marked_file_strips_for_every_combination_of_its_features(tracked_files):
    """The marker pass succeeds (no MarkerError) for every answer set.

    Structural errors - near-miss marker text, an END without a START, an END
    whose expression differs from its START, an unclosed START, an expression
    parse error or an unknown feature name - are raised the same way for every
    flag set: process_text walks every line and evaluates every START
    expression even when its enclosing block is off. One call per file, with
    every feature on, therefore finds all of them.

    The only flag-dependent error is "file became empty or whitespace-only
    after marker stripping". If any non-blank line sits outside every marker
    block the file can never become empty; otherwise every non-blank line is
    enclosed by some block, and the file empties only when a combination of
    the features named by those enclosing expressions (plus the PATHS owner
    expressions) removes them all. Those are a handful, not 2^n.
    """
    all_names = [feature.name for feature in features.FEATURES]
    all_on = {name: name != "_template" for name in all_names}

    def kept(flags, owners):
        return not any(not markers._eval_expr(features.PATHS[key], flags, False, key, 0) for key in owners)

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
        if not _marker_feature_names(text):
            continue
        owners = _owning_paths(rel)

        flags = dict(all_on)
        if not kept(flags, owners):
            flags["_template"] = True
            if not kept(flags, owners):
                continue  # no answer set keeps this file
        markers.process_text(text, flags, style, rel)

        has_outside, enclosures = _content_line_enclosures(text, style)
        if has_outside:
            checked += 1
            continue

        combo_names: set[str] = set()
        for enclosing in enclosures:
            for expr in enclosing:
                combo_names |= _expr_feature_names(expr)
        for key in owners:
            combo_names |= _expr_feature_names(features.PATHS[key])
        for values in itertools.product([False, True], repeat=len(combo_names)):
            combo_flags = dict.fromkeys(all_names, False)
            combo_flags.update(zip(sorted(combo_names), values))
            if not kept(combo_flags, owners):
                continue  # the file is deleted for this answer set, never processed
            markers.process_text(text, combo_flags, style, rel)
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
