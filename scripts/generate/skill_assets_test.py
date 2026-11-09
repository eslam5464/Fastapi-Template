"""Tests for scripts/generate/skill_assets.py.

The first tests check the real template snapshots; the rest check rebuild(),
which post_gen.py runs in every generated project.
"""

import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

import skill_assets  # noqa: E402

REFRESH = "uv run python scripts/generate/skill_assets.py --refresh"


def test_template_snapshots_are_current():
    problems = skill_assets.stale()
    assert problems == [], "\n".join([*problems, f"Run: {REFRESH}"])


def test_template_snapshots_have_no_markers():
    # A skill installed on its own (npx skills add, or a copy of the folder)
    # never runs the generator, so its snapshots must read as plain code.
    for asset_dir in skill_assets.ASSET_DIRS:
        for rel, path in skill_assets.snapshots(skill_assets.REPO_ROOT, asset_dir):
            assert "FEATURE[" not in path.read_text(encoding="utf-8"), f"{asset_dir}/{rel}: run {REFRESH}"


def test_full_flags_turn_every_service_on_and_template_content_off():
    flags = skill_assets.full_flags()
    assert flags.pop("_template") is False
    assert flags and all(flags.values())


def test_split_and_join_round_trip():
    header = skill_assets.PROJECT_NOTICE.format(
        start=skill_assets.NOTICE_START, end=skill_assets.NOTICE_END, rel="app/x.py"
    )
    for body in ("import os\n", "class A:\n    pass\n"):
        text = skill_assets.join(header, "app/x.py", body)
        assert skill_assets.split(text) == (header, body)
    assert skill_assets.join(header, "app/x.py", "class A:\n    pass\n").count("\n\n\n") == 1
    assert "\n\n\n" not in skill_assets.join(header, "Dockerfile", "FROM python\n")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _snapshot(rel: str, body: str) -> str:
    return skill_assets.join(skill_assets._template_notice(rel, "2026-01-01"), rel, body)


def test_rebuild_copies_project_files_and_drops_missing_ones(tmp_path):
    _write(tmp_path / "app/main.py", "import os\n\nVALUE = 1\n")
    _write(tmp_path / "Dockerfile", "FROM python:3.14\n")
    for asset_dir in skill_assets.ASSET_DIRS:
        base = tmp_path / asset_dir
        _write(base / "app/main.py", _snapshot("app/main.py", "import os\nimport redis\n"))
        _write(base / "Dockerfile", _snapshot("Dockerfile", "FROM python:3.12\n"))
        _write(base / "app/middleware/rate_limit.py", _snapshot("app/middleware/rate_limit.py", "X = 1\n"))

    skill_assets.rebuild(tmp_path)

    for asset_dir in skill_assets.ASSET_DIRS:
        base = tmp_path / asset_dir
        header, body = skill_assets.split((base / "app/main.py").read_text(encoding="utf-8"))
        assert body == "import os\n\nVALUE = 1\n"
        assert "as this project was generated" in header
        assert skill_assets.split((base / "Dockerfile").read_text(encoding="utf-8"))[1] == "FROM python:3.14\n"
        assert not (base / "app/middleware").exists()
        assert (base / "app").is_dir()


def test_rebuild_without_a_skill_folder_does_nothing(tmp_path):
    _write(tmp_path / "app/main.py", "import os\n")
    skill_assets.rebuild(tmp_path)
    assert sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")) == ["app", "app/main.py"]
