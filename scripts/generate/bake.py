"""Bake one generation variant with the real Copier flow.

The template CI and developers use this same command, so a variant that fails
in CI can be reproduced locally with one line:

    uv run python scripts/generate/bake.py --variant minimal --dest ../baked
    uv run python scripts/generate/bake.py --list

It runs `copier copy` with the variant's answers (see variants.py) in strict
mode (FASTAPI_TEMPLATE_STRICT=1), so a failing `uv lock` or ruff pass stops the
bake instead of printing a warning. `--vcs-ref HEAD` (the default) includes
uncommitted changes in this checkout.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_ROOT = SCRIPT_DIR.parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import variants  # noqa: E402


def copier_command(variant: str, dest: Path, vcs_ref: str) -> list[str]:
    known = variants.all_variants()
    if variant not in known:
        raise SystemExit(f"bake.py: unknown variant {variant!r}; choose one of: {', '.join(known)}")
    return [
        sys.executable,
        "-m",
        "copier",
        "copy",
        "--vcs-ref",
        vcs_ref,
        str(TEMPLATE_ROOT),
        str(dest),
        *variants.copier_data_args(known[variant]),
        "--defaults",
        "--trust",
        "--quiet",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--variant", help="variant name (see --list)")
    parser.add_argument("--dest", type=Path, help="directory to generate into (must not exist or be empty)")
    parser.add_argument("--vcs-ref", default="HEAD", help="git ref of the template to bake (default: HEAD)")
    parser.add_argument("--list", action="store_true", help="list the variant names and exit")
    args = parser.parse_args()

    if args.list:
        print("\n".join(variants.all_variants()))
        return
    if not args.variant or not args.dest:
        parser.error("--variant and --dest are required (or use --list)")

    env = {**os.environ, "FASTAPI_TEMPLATE_STRICT": "1"}
    result = subprocess.run(copier_command(args.variant, args.dest, args.vcs_ref), env=env)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
