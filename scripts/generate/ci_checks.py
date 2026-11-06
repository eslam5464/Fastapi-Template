"""Checks the template CI runs against a baked project (stdlib only).

    # In the baked project, with its own interpreter: import every app module.
    uv run --no-sync python <template>/scripts/generate/ci_checks.py import-app

    # Fail when the pytest run skipped any test (pytest --junitxml=junit.xml).
    python scripts/generate/ci_checks.py no-skips /tmp/baked/junit.xml

`import-app` runs after `uv sync --no-dev`, so it fails when application code
needs a package that only the test or dev groups install. `no-skips` makes a
silently skipped test (a missing optional SDK, a disabled feature) fail the
job instead of passing it.
"""

from __future__ import annotations

import argparse
import importlib
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Modules that are not plain application code: Alembic's env.py runs a
# migration when imported.
IMPORT_SKIP_PREFIXES = ("app.alembic",)


def app_modules(root: Path) -> list[str]:
    """Every module name under root/app (from the files, nothing imported), minus IMPORT_SKIP_PREFIXES."""
    names = []
    for path in (root / "app").rglob("*.py"):
        parts = path.relative_to(root).with_suffix("").parts
        if parts[-1] == "__init__":
            parts = parts[:-1]
        name = ".".join(parts)
        if name != "app" and not any(
            name == prefix or name.startswith(prefix + ".") for prefix in IMPORT_SKIP_PREFIXES
        ):
            names.append(name)
    return sorted(names)


def import_app(root: Path) -> int:
    root = root.resolve()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    names = app_modules(root)
    failures = []
    warnings = []
    for name in names:
        try:
            importlib.import_module(name)
        except ImportError as exc:  # a package or module this install does not provide
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
        except Exception as exc:
            # Module-level code that needs configuration (credentials, files) the
            # CI environment does not have. Its imports ran before that code, and
            # a missing package is what this check is for, so only report it.
            warnings.append(f"{name}: {type(exc).__name__}: {exc}")
    for failure in failures:
        print(f"FAIL {failure}")
    for warning in warnings:
        print(f"WARN {warning} (not an import error; needs configuration to load)")
    print(f"imported {len(names) - len(failures) - len(warnings)}/{len(names)} app modules")
    return 1 if failures or not names else 0


def skipped_tests(junit_xml: Path) -> list[str]:
    """`classname::name - reason` for every skipped test case in a JUnit XML report."""
    found = []
    for case in ET.parse(junit_xml).getroot().iter("testcase"):
        skipped = case.find("skipped")
        if skipped is not None:
            found.append(f"{case.get('classname')}::{case.get('name')} - {skipped.get('message', '')}")
    return found


def no_skips(junit_xml: Path) -> int:
    found = skipped_tests(junit_xml)
    for line in found:
        print(f"SKIPPED {line}")
    if found:
        print(f"{len(found)} test(s) skipped; every test must run in every variant.")
    return 1 if found else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    imports = commands.add_parser("import-app", help="import every module of the app package")
    imports.add_argument("root", nargs="?", type=Path, default=Path("."), help="baked project directory")
    skips = commands.add_parser("no-skips", help="fail if the JUnit report has skipped tests")
    skips.add_argument("junit_xml", type=Path)
    args = parser.parse_args()
    if args.command == "import-app":
        raise SystemExit(import_app(args.root))
    raise SystemExit(no_skips(args.junit_xml))


if __name__ == "__main__":
    main()
