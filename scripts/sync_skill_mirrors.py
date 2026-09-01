"""Keeps the fastapi-template-architect skill's Codex CLI mirror in sync with its
canonical Claude Code copy.

Codex CLI auto-discovers skills from `.agents/skills/<name>/` by walking up from cwd
to the repo root (marker: `.git`) - the same repo-ancestry trick Claude Code already
uses for `.claude/skills/<name>/` - and Codex's SKILL.md format is compatible with
Claude's (YAML frontmatter + optional scripts/references/assets). Rather than
hand-maintaining two copies that can silently drift, this script regenerates the
Codex mirror from the one canonical source, and the `sync-skill-mirrors` local
pre-commit hook (see .pre-commit-config.yaml) runs it in --check mode to fail the
commit if the mirror is stale.

Usage:
    uv run python scripts/sync_skill_mirrors.py           # regenerate the mirror
    uv run python scripts/sync_skill_mirrors.py --check   # fail if the mirror is stale
"""

import argparse
import filecmp
import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = "fastapi-template-architect"
CANONICAL = REPO_ROOT / ".claude" / "skills" / SKILL_NAME
MIRROR = REPO_ROOT / ".agents" / "skills" / SKILL_NAME

# `evals/` is a skill-authoring artifact (test prompts, not runtime content) and
# doesn't need to be mirrored - everything Codex actually reads is here.
MIRRORED_ENTRIES = ["SKILL.md", "references", "assets", "scripts"]


def build_mirror(dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for entry in MIRRORED_ENTRIES:
        src = CANONICAL / entry
        if not src.exists():
            raise SystemExit(f"sync_skill_mirrors.py: expected {src} to exist")
        if src.is_dir():
            shutil.copytree(src, dest / entry)
        else:
            shutil.copy2(src, dest / entry)


def _read_normalized(path: Path) -> str | bytes:
    # Compare text content with line endings normalized (Path.read_text() translates
    # \r\n/\r to \n) rather than raw bytes: this repo has no .gitattributes, and
    # Windows' core.autocrlf=true means a plain `git checkout` can flip a tracked
    # file between LF and CRLF on disk with no content change at all - a byte-level
    # comparison would spuriously flag that as drift. Falls back to raw bytes for
    # anything that isn't valid UTF-8 text (none of this skill's files today, but
    # future-proof against a binary asset being added).
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_bytes()


def dirs_match(a: Path, b: Path) -> bool:
    comparison = filecmp.dircmp(a, b)
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        return False
    for name in comparison.common_files:
        if _read_normalized(a / name) != _read_normalized(b / name):
            return False
    return all(dirs_match(a / sub, b / sub) for sub in comparison.common_dirs)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Don't write anything - exit 1 if the mirror is stale relative to the canonical skill.",
    )
    args = parser.parse_args()

    if not CANONICAL.exists():
        raise SystemExit(f"sync_skill_mirrors.py: canonical skill not found at {CANONICAL}")

    if args.check:
        with tempfile.TemporaryDirectory() as tmp:
            fresh = Path(tmp) / SKILL_NAME
            build_mirror(fresh)
            if not MIRROR.exists() or not dirs_match(fresh, MIRROR):
                print(
                    f"'{MIRROR.relative_to(REPO_ROOT)}' is out of sync with "
                    f"'{CANONICAL.relative_to(REPO_ROOT)}'. Run: "
                    f"uv run python scripts/sync_skill_mirrors.py",
                    file=sys.stderr,
                )
                sys.exit(1)
        print(f"'{MIRROR.relative_to(REPO_ROOT)}' is up to date.")
        return

    build_mirror(MIRROR)
    print(f"Synced '{CANONICAL.relative_to(REPO_ROOT)}' -> '{MIRROR.relative_to(REPO_ROOT)}'.")


if __name__ == "__main__":
    main()
