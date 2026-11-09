"""The skill's snapshot files and how they follow the live files.

Each file under the fastapi-template-architect skill's `assets/` folder is a
snapshot of the repo file at the same relative path (`assets/<rel>` is a copy
of `<rel>`): a short SNAPSHOT NOTICE header, then the file's content.

- In this template repo a snapshot is the live file rendered with every
  optional service on and template-only content off, with the FEATURE markers
  removed and Python re-formatted. A skill installed on its own (for example
  `npx skills add ... --skill fastapi-template-architect`, or a copy of the
  folder) never runs the generator, so it must read as clean, complete code.
  `--refresh` rewrites the snapshots (and the `.agents/` mirror); `--check`
  fails when one is stale. manifest_test.py runs the check.
- In a generated project, post_gen.py calls `rebuild()`: each snapshot becomes
  a copy of that project's own file, and the snapshots of files the project
  does not have are deleted.

Python 3.9 compatible: post_gen.py imports this module.

Usage (template repo):
    uv run python scripts/generate/skill_assets.py --refresh
    uv run python scripts/generate/skill_assets.py --check
"""

from __future__ import annotations

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import features  # noqa: E402
import markers  # noqa: E402

REPO_ROOT = SCRIPT_DIR.parent.parent
SKILL = "fastapi-template-architect"
CANONICAL_ASSETS = Path(".claude") / "skills" / SKILL / "assets"
ASSET_DIRS = (CANONICAL_ASSETS, Path(".agents") / "skills" / SKILL / "assets")

NOTICE_START = "# --- SNAPSHOT NOTICE (fastapi-template-architect skill) ---"
NOTICE_END = "# --- END SNAPSHOT NOTICE ---"
_DATE_RE = re.compile(r"taken (\d{4}-\d{2}-\d{2})")

TEMPLATE_NOTICE = """\
{start}
# Copy of {rel} from eslam5464/Fastapi-Template, taken {date},
# with every optional service included (a generated project only has the
# services chosen for it). The real repo is the source of truth; this is a
# fallback/reference copy for offline scaffolding and Extend/Audit-mode
# pattern-matching. Prefer driving the real Copier template
# (see references/copier-template-mechanics.md) whenever that's available.
{end}
"""

PROJECT_NOTICE = """\
{start}
# Copy of {rel} as this project was generated from eslam5464/Fastapi-Template.
# The project's own file is the source of truth; this copy is a reference for
# Extend/Audit-mode pattern-matching and drifts as the project changes.
{end}
"""

# ruff format puts two blank lines between a comment and a top-level def/class.
_TOP_LEVEL_DEF = re.compile(r"(?:async def |def |class |@)")


def _read(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def join(header: str, rel: str, body: str) -> str:
    """The header, the blank line(s) ruff expects after a comment block, then the body."""
    gap = "\n\n" if rel.endswith(".py") and _TOP_LEVEL_DEF.match(body) else "\n"
    return header + gap + body


def split(text: str) -> tuple[str, str]:
    """Split a snapshot into its notice header (through the END line) and its body."""
    text = text.replace("\r\n", "\n")
    if not text.startswith(NOTICE_START + "\n"):
        raise ValueError("snapshot does not start with the SNAPSHOT NOTICE header")
    end = text.find("\n" + NOTICE_END + "\n")
    if end == -1:
        raise ValueError("snapshot has no END SNAPSHOT NOTICE line")
    cut = end + len(NOTICE_END) + 2
    return text[:cut], text[cut:].lstrip("\n")


def snapshots(root: Path, asset_dir: Path) -> list[tuple[str, Path]]:
    """(relative path, snapshot path) for every snapshot under root/asset_dir."""
    base = root / asset_dir
    if not base.is_dir():
        return []
    return [(path.relative_to(base).as_posix(), path) for path in sorted(base.rglob("*")) if path.is_file()]


def full_flags() -> dict[str, bool]:
    """Every optional service on (computed ones included), template-only content off."""
    return {feature.name: feature.name != "_template" for feature in features.FEATURES}


def _ruff(args: list[str], text: str, rel: str, root: Path) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", *args, "--no-cache", "--quiet", "--stdin-filename", rel, "-"],
        input=text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=root,
    )
    if result.returncode not in (0, 1) or not result.stdout:
        raise RuntimeError(f"ruff {args[0]} failed on {rel}:\n{result.stderr}")
    return result.stdout.replace("\r\n", "\n")


def render_full(rel: str, root: Path = REPO_ROOT) -> str:
    """The body a template snapshot of `rel` must have."""
    text = _read(root / rel)
    style = markers.style_for(Path(rel))
    if style is not None:
        text = markers.process_text(text, full_flags(), style, rel)
    if rel.endswith(".py"):
        # Removing marker lines can split an import block in two; re-sort and
        # re-format the way the project's own ruff hooks expect.
        text = _ruff(["check", "--select", "I", "--fix", "--exit-zero"], text, rel, root)
        text = _ruff(["format"], text, rel, root)
    return text.lstrip("\n")


def stale(root: Path = REPO_ROOT) -> list[str]:
    """Template snapshots whose body or header is not what --refresh would write."""
    problems = []
    for rel, path in snapshots(root, CANONICAL_ASSETS):
        if not (root / rel).is_file():
            problems.append(f"{rel}: snapshot of a file the template does not have")
            continue
        try:
            header, body = split(_read(path))
        except ValueError as exc:
            problems.append(f"{rel}: {exc}")
            continue
        if body != render_full(rel, root):
            problems.append(f"{rel}: body differs from the live file rendered with every service on")
        match = _DATE_RE.search(header)
        if not match or header != _template_notice(rel, match.group(1)):
            problems.append(f"{rel}: notice header is not the current wording")
    return problems


def _template_notice(rel: str, date: str) -> str:
    return TEMPLATE_NOTICE.format(start=NOTICE_START, end=NOTICE_END, rel=rel, date=date)


def refresh(root: Path = REPO_ROOT) -> list[str]:
    """Rewrite the stale template snapshots, then the `.agents/` mirror. Returns the rewritten paths."""
    today = datetime.date.today().isoformat()
    written = []
    for rel, path in snapshots(root, CANONICAL_ASSETS):
        if not (root / rel).is_file():
            raise SystemExit(f"skill_assets.py: {path} is a snapshot of {rel}, which does not exist")
        current = _read(path)
        try:
            header, body = split(current)
        except ValueError:
            header, body = "", None
        expected = render_full(rel, root)
        match = _DATE_RE.search(header)
        date = match.group(1) if (match and body == expected) else today
        text = join(_template_notice(rel, date), rel, expected)
        if text != current:
            path.write_bytes(text.encode("utf-8"))
            written.append(rel)
    subprocess.run([sys.executable, str(root / "scripts" / "sync_skill_mirrors.py")], check=True, cwd=root)
    return written


def rebuild(root: Path) -> None:
    """In a generated project: make every snapshot a copy of the project's own file.

    The snapshot of a file the project does not have (a service that was not
    chosen) is deleted, with any folder that leaves empty.
    """
    for asset_dir in ASSET_DIRS:
        base = root / asset_dir
        for rel, path in snapshots(root, asset_dir):
            live = root / rel
            if live.is_file():
                header = PROJECT_NOTICE.format(start=NOTICE_START, end=NOTICE_END, rel=rel)
                path.write_bytes(join(header, rel, _read(live).lstrip("\n")).encode("utf-8"))
            else:
                path.unlink()
                markers._remove_empty_parents(path.parent, base)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--refresh", action="store_true", help="rewrite stale template snapshots and the mirror")
    group.add_argument("--check", action="store_true", help="exit 1 when a template snapshot is stale")
    args = parser.parse_args()
    if args.refresh:
        for rel in refresh():
            print(f"refreshed {rel}")
        return
    problems = stale()
    for problem in problems:
        print(problem)
    if problems:
        print("Run: uv run python scripts/generate/skill_assets.py --refresh")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
