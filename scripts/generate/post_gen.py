"""Copier post-generation task: runs in the generated project's directory.

Every value that needs to differ between this repo (run directly) and a
generated project is substituted here, directly on the real files copier just
copied — there are no `.jinja`-suffixed twin files to keep in sync.

Optional-feature stripping (Apple Pay etc.) and template-only sections are
handled by the marker engine in markers.py, driven by the feature manifest in
features.py and the resolved feature flags passed via --features-json.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import features  # noqa: E402
import markers  # noqa: E402
import skill_assets  # noqa: E402

PY_VERSION_FILES = [
    Path("Dockerfile"),
    Path("pyproject.toml"),
    Path("docs/deployment.md"),
    Path("docs/development.md"),
    Path("docs/guides/getting-started.md"),
]

LICENSE_RE = re.compile(r"Copyright \(c\) (\d{4}) ([^\r\n]+)")


def _read(path: Path) -> str:
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def _write(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def replace_required(path: Path, old: str, new: str) -> None:
    content = _read(path)
    match_old = old
    match_new = new
    if "\r\n" in content and "\n" in old and "\r" not in old:
        match_old = old.replace("\n", "\r\n")
        match_new = new.replace("\n", "\r\n")
    if match_old not in content:
        raise SystemExit(f"post_gen.py: expected content not found in {path}: {old!r}")
    _write(path, content.replace(match_old, match_new))


def resolve(raw: dict) -> dict[str, bool]:
    """Turn the raw answers dict into a feature name -> on/off flag map.

    ``raw`` keys must be exactly ``{"services"}`` plus every ``Feature.question``
    in ``features.FEATURES``. ``services`` selects the minimal base (no optional
    features) or per-service answers; every ``include_*`` value must be a bool.
    """
    questions = {feature.question for feature in features.FEATURES if feature.question}
    expected = {"services"} | questions

    unknown = sorted(set(raw) - expected)
    if unknown:
        raise SystemExit(f"post_gen.py: unknown feature answer(s): {', '.join(unknown)}")
    missing = sorted(expected - set(raw))
    if missing:
        raise SystemExit(f"post_gen.py: missing feature answer(s): {', '.join(missing)}")

    services = raw["services"]
    if services not in ("minimal", "custom"):
        raise SystemExit(f"post_gen.py: services must be 'minimal' or 'custom', got {services!r}")

    answers: dict[str, bool] = {}
    for question in sorted(questions):
        value = raw[question]
        if not isinstance(value, bool):
            raise SystemExit(f"post_gen.py: {question} must be a bool, got {value!r}")
        answers[question] = value

    if services == "minimal":
        enabled = [question for question in sorted(answers) if answers[question]]
        if enabled:
            raise SystemExit(
                "post_gen.py: " + "; ".join(f"{question}=true requires services=custom" for question in enabled)
            )

    flags: dict[str, bool] = {}
    for feature in features.FEATURES:
        if feature.name == "_template":
            flags[feature.name] = False
        elif feature.computed_from:
            flags[feature.name] = any(flags[source] for source in feature.computed_from)
        else:
            value = answers[feature.question]
            if feature.parent is not None and value and not flags[feature.parent]:
                raise SystemExit(
                    f"post_gen.py: {feature.question}=true requires its parent feature "
                    f"'{feature.parent}' to be enabled too"
                )
            flags[feature.name] = value
    return flags


def capture_source_python_version() -> str:
    return _read(Path(".python-version")).strip()


def capture_license_year_and_author() -> tuple[str, str]:
    content = _read(Path("LICENSE"))
    match = LICENSE_RE.search(content)
    if match is None:
        raise SystemExit("post_gen.py: could not find 'Copyright (c) YYYY Name' line in LICENSE")
    return match.group(1), match.group(2)


def bump_python_version(old_version: str, new_version: str) -> None:
    pattern = re.compile(rf"(?<![\d.]){re.escape(old_version)}(?![\d.])")
    for path in PY_VERSION_FILES:
        content = _read(path)
        new_content, count = pattern.subn(new_version, content)
        if count == 0:
            raise SystemExit(f"post_gen.py: expected Python version {old_version!r} not found in {path}")
        _write(path, new_content)

    old_ruff_target = "py" + old_version.replace(".", "")
    new_ruff_target = "py" + new_version.replace(".", "")
    replace_required(
        Path("pyproject.toml"),
        f'target-version = "{old_ruff_target}"',
        f'target-version = "{new_ruff_target}"',
    )

    _write(Path(".python-version"), f"{new_version}\n")


def rewrite_license(old_year: str, old_author: str, new_author: str) -> None:
    new_year = str(datetime.now().year)
    replace_required(
        Path("LICENSE"),
        f"Copyright (c) {old_year} {old_author}",
        f"Copyright (c) {new_year} {new_author}",
    )


def apply_identity_substitutions(args: argparse.Namespace) -> None:
    slug_us = args.project_slug.replace("-", "_")

    pyproject = Path("pyproject.toml")
    replace_required(pyproject, 'name = "FastApi-Template"', f'name = "{args.project_slug}"')
    replace_required(pyproject, 'version = "1.2.0"', 'version = "0.1.0"')
    replace_required(
        pyproject,
        'description = "A FastAPI project template"',
        f'description = "{args.project_description}"',
    )
    replace_required(
        pyproject,
        'authors = [{ name = "Eslam", email = "eslam5464@users.noreply.github.com" }]',
        f'authors = [{{ name = "{args.author_name}", email = "{args.author_email}" }}]',
    )

    replace_required(Path("docker-compose.yml"), "fastapi_template", slug_us)
    replace_required(Path(".env.example"), "fastapi_template", slug_us)

    replace_required(Path(".github/CODEOWNERS"), "@Eslam5464", f"@{args.github_username}")

    # .github/copilot-instructions.md is generic (no project name or
    # @Eslam5464 reference) — it applies verbatim to every generated
    # project, so there is nothing to substitute here.

    readme = Path("README.md")
    replace_required(readme, "# FastAPI Template", f"# {args.project_name}")
    replace_required(readme, "eslam5464/Fastapi-Template", f"{args.github_username}/{args.project_slug}")
    replace_required(
        readme,
        "A production-ready FastAPI project template with modern best practices, "
        "async support, and PostgreSQL integration.",
        args.project_description,
    )
    replace_required(
        readme,
        "git clone <your-repo-url>",
        f"git clone https://github.com/{args.github_username}/{args.project_slug}.git",
    )
    replace_required(readme, "cd FastApi-Template", f"cd {args.project_slug}")

    development_doc = Path("docs/development.md")
    replace_required(
        development_doc,
        "with the FastAPI Template, including",
        f"with {args.project_name}, including",
    )
    replace_required(development_doc, "fastapi_template", slug_us)
    replace_required(development_doc, "cd FastApi-Template", f"cd {args.project_slug}")

    deployment_doc = Path("docs/deployment.md")
    replace_required(deployment_doc, "for the FastAPI Template.", f"for {args.project_name}.")
    replace_required(deployment_doc, "The FastAPI Template supports", f"{args.project_name} supports")
    replace_required(deployment_doc, "fastapi_template", slug_us)

    replace_required(Path("docs/guides/getting-started.md"), "cd Fastapi-Template", f"cd {args.project_slug}")


def run_quiet(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kwargs)


def regenerate_lockfile(python_version: str) -> None:
    try:
        run_quiet(["uv", "python", "install", python_version], timeout=120)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass

    try:
        run_quiet(["uv", "lock"])
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        message = (
            f"could not regenerate uv.lock automatically (Python {python_version} "
            f"may not be installed). Run 'uv python install {python_version}' then 'uv sync' yourself."
        )
        if os.environ.get("FASTAPI_TEMPLATE_STRICT") == "1":
            stderr = getattr(exc, "stderr", None)
            detail = f"\n{stderr}" if stderr else ""
            raise SystemExit(f"post_gen.py: {message}{detail}") from exc
        print(f"Warning: {message}")


def offline_mode() -> bool:
    """FASTAPI_TEMPLATE_OFFLINE=1: the offline variant checker (check_variants.py).

    Skips the steps that need the network or a real project checkout (uv lock,
    git init) and runs ruff from the current interpreter instead of uvx.
    """
    return os.environ.get("FASTAPI_TEMPLATE_OFFLINE") == "1"


def hook_rev(repo: str) -> str:
    """The `rev:` (without a leading "v") pinned for a hook repo in .pre-commit-config.yaml."""
    match = re.search(re.escape(repo) + r"\s*\n\s*rev:\s*v?(\S+)", _read(Path(".pre-commit-config.yaml")))
    if match is None:
        name = repo.rsplit("/", 1)[-1]
        raise SystemExit(f"post_gen.py: could not find the {name} rev in .pre-commit-config.yaml")
    return match.group(1)


def ruff_version() -> str:
    return hook_rev("astral-sh/ruff-pre-commit")


def detect_secrets_exclude() -> re.Pattern:
    """The `exclude:` regex of the detect-secrets hook in .pre-commit-config.yaml."""
    text = _read(Path(".pre-commit-config.yaml"))
    start = text.find("id: detect-secrets")
    if start == -1:
        raise SystemExit("post_gen.py: could not find the detect-secrets hook in .pre-commit-config.yaml")
    hook = re.split(r"\n\s*- (?:id|repo):", text[start:], maxsplit=1)[0]
    match = re.search(r"\n\s*exclude:\s*(\S+)", hook)
    return re.compile(match.group(1) if match else r"(?!)")


def normalize_python(files: list[Path]) -> None:
    """Re-sort imports and re-format the Python files the marker pass rewrote.

    ruff always keeps a blank line between an import and a comment that follows
    it, so a FEATURE marker sitting between two imports leaves that blank line
    behind once the marker line is removed, splitting one import block in two.
    Running ruff's import sorter and formatter (the version the generated
    project's pre-commit config pins) on the touched files restores the layout
    the project's own lint hooks expect.
    """
    py_files = [str(path) for path in files if path.suffix == ".py"]
    if not py_files:
        return
    ruff = [sys.executable, "-m", "ruff"] if offline_mode() else ["uvx", f"ruff@{ruff_version()}"]
    try:
        # --no-cache: don't leave a .ruff_cache/ directory in the generated project.
        run_quiet([*ruff, "check", "--select", "I", "--fix", "--no-cache", "--quiet", *py_files])
        run_quiet([*ruff, "format", "--no-cache", "--quiet", *py_files])
    except (OSError, subprocess.CalledProcessError) as exc:
        message = (
            "could not normalise imports in the generated files with ruff. "
            "Run 'uv run ruff check --fix' and 'uv run ruff format' yourself."
        )
        if os.environ.get("FASTAPI_TEMPLATE_STRICT") == "1":
            output = getattr(exc, "stdout", None) or ""
            stderr = getattr(exc, "stderr", None) or ""
            detail = f"\n{output}{stderr}" if (output or stderr) else ""
            raise SystemExit(f"post_gen.py: {message}{detail}") from exc
        print(f"Warning: {message}")


def remove_generate_tooling() -> None:
    # This script only exists to run this task; it has no purpose in a
    # generated project, so it removes its own directory as its last act.
    shutil.rmtree(Path(__file__).resolve().parent, ignore_errors=True)


def refresh_secrets_baseline() -> None:
    """Update the line numbers in .secrets.baseline after the marker pass.

    Removing a feature block moves the lines below it, so the known (allowed)
    test secrets recorded in the baseline end up on other line numbers. The
    detect-secrets pre-commit hook would then rewrite the baseline and fail,
    breaking the generated project's first `pre-commit run` and its CI lint
    job. Running the same hook here, on the files `pre-commit run --all-files`
    gives it, puts the updated baseline into the initial commit instead.

    Runs after `git add -A`, so `git ls-files` lists the project files.
    """
    if not Path(".secrets.baseline").is_file():
        return
    exclude = detect_secrets_exclude()
    files = [name for name in run_quiet(["git", "ls-files"]).stdout.splitlines() if name and not exclude.search(name)]
    cmd = [
        "uvx",
        "--from",
        f"detect-secrets=={hook_rev('Yelp/detect-secrets')}",
        "detect-secrets-hook",
        "--baseline",
        ".secrets.baseline",
        *files,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as exc:
        detail = str(exc)
    else:
        # Exit code 0: the baseline was already right; 3: it was updated.
        if result.returncode in (0, 3):
            return
        detail = f"exit code {result.returncode}\n{result.stdout}{result.stderr}".rstrip()
    message = (
        "could not refresh .secrets.baseline with detect-secrets. Run "
        "'uv run pre-commit run detect-secrets --all-files' and commit the updated baseline yourself."
    )
    if os.environ.get("FASTAPI_TEMPLATE_STRICT") == "1":
        raise SystemExit(f"post_gen.py: {message}\n{detail}")
    print(f"Warning: {message}")


def git_init_and_commit() -> None:
    try:
        run_quiet(["git", "init"])
        run_quiet(["git", "add", "-A"])
        refresh_secrets_baseline()
        run_quiet(["git", "add", "-A"])
        run_quiet(["git", "commit", "-m", "chore: initial commit from copier template"])
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"Warning: could not initialize git repository automatically ({exc}). Run 'git init' yourself.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--project-slug", required=True)
    parser.add_argument("--project-description", required=True)
    parser.add_argument("--author-name", required=True)
    parser.add_argument("--author-email", required=True)
    parser.add_argument("--github-username", required=True)
    parser.add_argument("--python-version", required=True)
    parser.add_argument("--features-json", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    flags = resolve(json.loads(args.features_json))

    old_python_version = capture_source_python_version()
    old_license_year, old_license_author = capture_license_year_and_author()

    bump_python_version(old_python_version, args.python_version)
    apply_identity_substitutions(args)
    rewrite_license(old_license_year, old_license_author, args.author_name)

    try:
        changed = markers.apply(Path("."), flags)
    except markers.MarkerError as exc:
        raise SystemExit(f"post_gen.py: {exc}") from exc
    normalize_python(changed)
    # The skill's snapshots become copies of this project's own files.
    skill_assets.rebuild(Path("."))

    if not offline_mode():
        regenerate_lockfile(args.python_version)
    remove_generate_tooling()
    if not offline_mode():
        git_init_and_commit()


if __name__ == "__main__":
    main()
