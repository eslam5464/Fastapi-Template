"""Fast, offline check of every generation variant (no network, no Copier, no DB).

For each variant from variants.py it copies the files Copier would copy into a
temp directory, runs the real post_gen.py there in offline mode (no uv lock, no
git, ruff from this interpreter), and then checks the result:

- every .py file parses, every .toml/.yml/.yaml file loads;
- import closure: every `app.*` / `tests.*` import resolves to a module that
  exists in the variant, and every third-party import is allowed for the
  enabled features (features.BASE_IMPORTS, Feature.imports, TEST_IMPORTS under
  tests/) - this catches code that still needs a package the variant dropped;
- forbidden tokens: patterns of features that are off do not appear in code;
- `ruff check` and `ruff format --check` pass on the whole variant.

It complements the slow bake tests and the template CI (real Copier, uv lock,
pytest, Docker). Run it after editing markers:

    uv run python scripts/generate/check_variants.py            # all variants
    uv run python scripts/generate/check_variants.py minimal    # some variants
    uv run python scripts/generate/check_variants.py --tree ../baked minimal   # a real bake
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import tomllib
import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_ROOT = SCRIPT_DIR.parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import features  # noqa: E402
import skill_assets  # noqa: E402
import variants  # noqa: E402

FIRST_PARTY = ("app", "tests")
# Where forbidden tokens of disabled features are looked for.
FORBIDDEN_SCOPE = ("app/**", "tests/**", "main.py", "*.toml", ".env.example", "README.md", "docs/**")
# The prose docs, also checked against each feature's doc_forbidden patterns.
DOC_SCOPE = ("README.md", "docs/**")
# Not checked: a domain-agnostic architecture guide whose Redis/Celery/cache
# mentions are illustrative patterns, and the template's own release history.
DOC_EXCLUDE = ("docs/backend-architecture.md", "docs/changelog/**")

IDENTITY_ARGS = [
    "--project-name",
    "FastAPI Template",
    "--project-slug",
    "fastapi-template",
    "--project-description",
    "A production-ready FastAPI backend with async PostgreSQL, JWT auth, and clean architecture.",
    "--author-name",
    "Eslam",
    "--author-email",
    "eslam5464@users.noreply.github.com",
    "--github-username",
    "eslam5464",
    "--python-version",
    "3.14",
]


def _copier_excluded(rel: str, patterns: list[str]) -> bool:
    parts = rel.split("/")
    return any(fnmatch.fnmatch(rel, p) or any(fnmatch.fnmatch(part, p) for part in parts) for p in patterns)


def template_files() -> list[str]:
    """The repo-relative files Copier copies: tracked + untracked, minus copier.yml's _exclude."""
    output = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard"],
        cwd=TEMPLATE_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    patterns = yaml.safe_load((TEMPLATE_ROOT / "copier.yml").read_text(encoding="utf-8"))["_exclude"]
    return [
        rel
        for rel in output.splitlines()
        if rel and (TEMPLATE_ROOT / rel).is_file() and not _copier_excluded(rel, patterns)
    ]


def generate(raw: dict, dest: Path, files: list[str]) -> None:
    """Copy the template files into dest and run post_gen.py there in offline mode."""
    for rel in files:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(TEMPLATE_ROOT / rel, target)
    env = {**os.environ, "FASTAPI_TEMPLATE_OFFLINE": "1", "FASTAPI_TEMPLATE_STRICT": "1"}
    result = subprocess.run(
        [sys.executable, "scripts/generate/post_gen.py", *IDENTITY_ARGS, "--features-json", json.dumps(raw)],
        cwd=dest,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"post_gen.py failed:\n{result.stdout}{result.stderr}")


def _module_exists(root: Path, module: str) -> bool:
    path = root.joinpath(*module.split("."))
    return path.with_suffix(".py").is_file() or path.is_dir()


def _imports(tree: ast.AST) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.lineno, node.module))
    return found


def _snapshot_problems(root: Path) -> list[str]:
    """Every skill snapshot is a copy of a file this variant ships, with the same content."""
    problems = []
    for asset_dir in skill_assets.ASSET_DIRS:
        for rel, path in skill_assets.snapshots(root, asset_dir):
            where = f"{asset_dir.as_posix()}/{rel}"
            live = root / rel
            if not live.is_file():
                problems.append(f"{where}: snapshot of {rel}, which this variant does not ship")
                continue
            try:
                _, body = skill_assets.split(path.read_text(encoding="utf-8"))
            except ValueError as exc:
                problems.append(f"{where}: {exc}")
                continue
            if "FEATURE[" in body or body != live.read_text(encoding="utf-8").lstrip("\n"):
                problems.append(f"{where}: differs from {rel}")
    return problems


def check_tree(root: Path, raw: dict) -> list[str]:
    """Problems found in a generated tree (empty list = clean)."""
    problems: list[str] = []
    enabled = set(variants.all_enabled_features(raw))
    allowed = set(sys.stdlib_module_names) | set(features.BASE_IMPORTS)
    for name in enabled:
        allowed |= set(features.FEATURES_BY_NAME[name].imports)
    test_allowed = allowed | set(features.TEST_IMPORTS)
    disabled = [feature for feature in features.FEATURES if feature.name != "_template" and feature.name not in enabled]
    forbidden = [re.compile(pattern) for feature in disabled for pattern in feature.forbidden]
    doc_forbidden = forbidden + [re.compile(pattern) for feature in disabled for pattern in feature.doc_forbidden]

    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.parts or ".venv" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        if path.suffix == ".py":
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), rel)
            except SyntaxError as exc:
                problems.append(f"{rel}:{exc.lineno}: does not parse: {exc.msg}")
                continue
            if rel.split("/")[0] in FIRST_PARTY or rel == "main.py":
                ok = test_allowed if rel.startswith("tests/") else allowed
                for line, module in _imports(tree):
                    top = module.split(".")[0]
                    if top in FIRST_PARTY:
                        if not _module_exists(root, module):
                            problems.append(f"{rel}:{line}: imports {module}, which this variant does not ship")
                    elif top not in ok:
                        problems.append(f"{rel}:{line}: imports third-party {top!r}, not allowed for this variant")
        elif path.suffix == ".toml":
            try:
                tomllib.loads(path.read_text(encoding="utf-8"))
            except tomllib.TOMLDecodeError as exc:
                problems.append(f"{rel}: invalid TOML: {exc}")
        elif path.suffix in (".yml", ".yaml"):
            try:
                list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
            except yaml.YAMLError as exc:
                problems.append(f"{rel}: invalid YAML: {exc}")

        if any(fnmatch.fnmatch(rel, glob) for glob in DOC_EXCLUDE):
            continue
        is_doc = any(fnmatch.fnmatch(rel, glob) for glob in DOC_SCOPE)
        patterns = doc_forbidden if is_doc else forbidden
        if patterns and any(fnmatch.fnmatch(rel, glob) for glob in FORBIDDEN_SCOPE):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    line = text.count("\n", 0, match.start()) + 1
                    problems.append(f"{rel}:{line}: contains {pattern.pattern!r} of a disabled feature")

    problems.extend(_snapshot_problems(root))

    for args in (["check", "--no-cache", "."], ["format", "--no-cache", "--check", "."]):
        result = subprocess.run([sys.executable, "-m", "ruff", *args], cwd=root, capture_output=True, text=True)
        if result.returncode != 0:
            problems.append(f"ruff {args[0]} failed:\n{result.stdout}{result.stderr}".rstrip())
    return problems


def check_variant(name: str, raw: dict, files: list[str] | None = None) -> list[str]:
    files = template_files() if files is None else files
    with tempfile.TemporaryDirectory(prefix=f"variant-{name}-") as tmp:
        dest = Path(tmp)
        try:
            generate(raw, dest, files)
        except RuntimeError as exc:
            return [str(exc)]
        return check_tree(dest, raw)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("variants", nargs="*", help="variant names (default: all; see variants.py)")
    parser.add_argument(
        "--tree",
        type=Path,
        help="check this already generated project (e.g. a real Copier bake) as the one variant given",
    )
    args = parser.parse_args()

    known = variants.all_variants()
    if args.tree is not None:
        if len(args.variants) != 1 or args.variants[0] not in known:
            raise SystemExit(f"--tree needs exactly one variant name; choose from: {', '.join(known)}")
        problems = check_tree(args.tree, known[args.variants[0]])
        print(f"{'FAIL' if problems else 'ok  '} {args.variants[0]} ({args.tree})")
        for problem in problems:
            print(f"     {problem}")
        raise SystemExit(1 if problems else 0)
    names = args.variants or list(known)
    unknown = [name for name in names if name not in known]
    if unknown:
        raise SystemExit(f"unknown variant(s): {', '.join(unknown)}; choose from: {', '.join(known)}")

    files = template_files()
    failed = 0
    for name in names:
        problems = check_variant(name, known[name], files)
        print(f"{'FAIL' if problems else 'ok  '} {name}")
        for problem in problems:
            print(f"     {problem}")
        failed += bool(problems)
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
