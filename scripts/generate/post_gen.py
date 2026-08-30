"""Copier post-generation task: runs in the generated project's directory.

Every value that needs to differ between this repo (run directly) and a
generated project is substituted here, directly on the real files copier just
copied — there are no `.jinja`-suffixed twin files to keep in sync.
"""

import argparse
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

APPLE_PAY_MARKERS = ("# --- APPLE_PAY_START ---", "# --- APPLE_PAY_END ---")
APPLE_PAY_SETTINGS_MARKERS = (
    "# --- APPLE_PAY_SETTINGS_START ---",
    "# --- APPLE_PAY_SETTINGS_END ---",
)
APPLE_PAY_PROPERTY_MARKERS = (
    "# --- APPLE_PAY_PROPERTY_START ---",
    "# --- APPLE_PAY_PROPERTY_END ---",
)
APPLE_PAY_ENV_MARKERS = ("# --- APPLE_PAY_ENV_START ---", "# --- APPLE_PAY_ENV_END ---")
APPLE_PAY_PYPROJECT_EXTRA_MARKERS = (
    "# --- APPLE_PAY_PYPROJECT_EXTRA_START ---",
    "# --- APPLE_PAY_PYPROJECT_EXTRA_END ---",
)
APPLE_PAY_MYPY_OVERRIDE_MARKERS = (
    "# --- APPLE_PAY_MYPY_OVERRIDE_START ---",
    "# --- APPLE_PAY_MYPY_OVERRIDE_END ---",
)
TEMPLATE_TOOLING_MARKERS = ("# --- TEMPLATE_TOOLING_START ---", "# --- TEMPLATE_TOOLING_END ---")
TEMPLATE_TOOLING_DEV_DEP_MARKERS = (
    "# --- TEMPLATE_TOOLING_DEV_DEP_START ---",
    "# --- TEMPLATE_TOOLING_DEV_DEP_END ---",
)
TEMPLATE_SECTION_MARKERS = ("<!-- TEMPLATE_SECTION_START -->", "<!-- TEMPLATE_SECTION_END -->")

PY_VERSION_FILES = [
    Path("Dockerfile"),
    Path("docker-compose.yml"),
    Path("pyproject.toml"),
    Path("docs/deployment.md"),
    Path("docs/development.md"),
    Path("docs/guides/getting-started.md"),
]

LICENSE_RE = re.compile(r"Copyright \(c\) (\d{4}) (.+)")


def replace_required(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    if old not in content:
        raise SystemExit(f"post_gen.py: expected content not found in {path}: {old!r}")
    path.write_text(content.replace(old, new), encoding="utf-8")


def strip_marked_block(path: Path, start_marker: str, end_marker: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if start_marker in line), None)
    end = next((i for i, line in enumerate(lines) if end_marker in line), None)
    if start is None or end is None:
        raise SystemExit(f"post_gen.py: markers {start_marker!r}/{end_marker!r} not found in {path}")
    del lines[start : end + 1]

    # Deleting the block can leave 3+ consecutive blank lines behind (blank
    # lines from both sides of the removed block collapsing together), which
    # trips ruff's isort/formatting checks. Collapse runs down to at most 2,
    # matching standard top-level class/def spacing.
    collapsed: list[str] = []
    blank_run = 0
    for line in lines:
        if line.strip() == "":
            blank_run += 1
            if blank_run > 2:
                continue
        else:
            blank_run = 0
        collapsed.append(line)

    path.write_text("".join(collapsed), encoding="utf-8")


def capture_source_python_version() -> str:
    return Path(".python-version").read_text(encoding="utf-8").strip()


def capture_license_year_and_author() -> tuple[str, str]:
    content = Path("LICENSE").read_text(encoding="utf-8")
    match = LICENSE_RE.search(content)
    if match is None:
        raise SystemExit("post_gen.py: could not find 'Copyright (c) YYYY Name' line in LICENSE")
    return match.group(1), match.group(2)


def bump_python_version(old_version: str, new_version: str) -> None:
    pattern = re.compile(rf"(?<![\d.]){re.escape(old_version)}(?![\d.])")
    for path in PY_VERSION_FILES:
        content = path.read_text(encoding="utf-8")
        new_content, count = pattern.subn(new_version, content)
        if count == 0:
            raise SystemExit(f"post_gen.py: expected Python version {old_version!r} not found in {path}")
        path.write_text(new_content, encoding="utf-8")

    old_ruff_target = "py" + old_version.replace(".", "")
    new_ruff_target = "py" + new_version.replace(".", "")
    replace_required(
        Path("pyproject.toml"),
        f'target-version = "{old_ruff_target}"',
        f'target-version = "{new_ruff_target}"',
    )

    Path(".python-version").write_text(f"{new_version}\n", encoding="utf-8")


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
    replace_required(pyproject, 'version = "1.1.1"', 'version = "0.1.0"')
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

    copilot = Path(".github/copilot-instructions.md")
    replace_required(copilot, "is FastAPI Template,", f"is {args.project_name},")
    replace_required(copilot, "@Eslam5464", f"@{args.github_username}")

    readme = Path("README.md")
    replace_required(readme, "# FastAPI Template", f"# {args.project_name}")
    replace_required(readme, "eslam5464/Fastapi-Template", f"{args.github_username}/{args.project_slug}")
    replace_required(
        readme,
        "A production-ready FastAPI project template with modern best practices, "
        "async support, JWT authentication, and PostgreSQL integration.",
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


def remove_apple_pay() -> None:
    apple_pay_module = Path("app/services/payments/apple_pay.py")
    if apple_pay_module.exists():
        apple_pay_module.unlink()
        payments_dir = apple_pay_module.parent
        if payments_dir.exists() and not any(payments_dir.iterdir()):
            payments_dir.rmdir()

    apple_pay_exceptions = Path("app/core/exceptions/apple_pay.py")
    if apple_pay_exceptions.exists():
        apple_pay_exceptions.unlink()

    payments_tests_dir = Path("tests/services/payments")
    if payments_tests_dir.exists():
        shutil.rmtree(payments_tests_dir)

    credentials_path = Path("app/core/credentials.py")
    strip_marked_block(credentials_path, *APPLE_PAY_MARKERS)
    content = credentials_path.read_text(encoding="utf-8")
    content = content.replace(
        "from pydantic import BaseModel, ConfigDict, Field, model_validator",
        "from pydantic import BaseModel, ConfigDict, model_validator",
    )
    credentials_path.write_text(content, encoding="utf-8")

    config_path = Path("app/core/config.py")
    content = config_path.read_text(encoding="utf-8")
    content = content.replace(
        "from app.core.credentials import ApplePayStoreCredentials, FirebaseServiceAccount",
        "from app.core.credentials import FirebaseServiceAccount",
    )
    config_path.write_text(content, encoding="utf-8")
    strip_marked_block(config_path, *APPLE_PAY_SETTINGS_MARKERS)
    strip_marked_block(config_path, *APPLE_PAY_PROPERTY_MARKERS)

    strip_marked_block(Path(".env.example"), *APPLE_PAY_ENV_MARKERS)
    strip_marked_block(Path("pyproject.toml"), *APPLE_PAY_PYPROJECT_EXTRA_MARKERS)
    strip_marked_block(Path("pyproject.toml"), *APPLE_PAY_MYPY_OVERRIDE_MARKERS)

    readme = Path("README.md")
    replace_required(readme, ", Apple Pay", "")
    replace_required(readme, "uv sync --extra apple-services\n", "")


def strip_template_only_sections() -> None:
    pyproject = Path("pyproject.toml")
    strip_marked_block(pyproject, *TEMPLATE_TOOLING_MARKERS)
    strip_marked_block(pyproject, *TEMPLATE_TOOLING_DEV_DEP_MARKERS)
    strip_marked_block(Path("README.md"), *TEMPLATE_SECTION_MARKERS)


def run_quiet(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kwargs)


def regenerate_lockfile(python_version: str) -> None:
    try:
        run_quiet(["uv", "python", "install", python_version], timeout=120)
    except OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired:
        pass

    try:
        run_quiet(["uv", "lock"])
    except OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired:
        print(
            f"Warning: could not regenerate uv.lock automatically (Python {python_version} "
            f"may not be installed). Run 'uv python install {python_version}' then 'uv sync' yourself."
        )


def remove_generate_tooling() -> None:
    # This script only exists to run this task; it has no purpose in a
    # generated project, so it removes its own directory as its last act.
    shutil.rmtree(Path(__file__).resolve().parent, ignore_errors=True)


def git_init_and_commit() -> None:
    try:
        run_quiet(["git", "init"])
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
    parser.add_argument("--include-apple-pay", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    include_apple_pay = args.include_apple_pay.strip().lower() == "true"

    old_python_version = capture_source_python_version()
    old_license_year, old_license_author = capture_license_year_and_author()

    bump_python_version(old_python_version, args.python_version)
    apply_identity_substitutions(args)
    rewrite_license(old_license_year, old_license_author, args.author_name)

    if not include_apple_pay:
        remove_apple_pay()
    strip_template_only_sections()

    regenerate_lockfile(args.python_version)
    remove_generate_tooling()
    git_init_and_commit()


if __name__ == "__main__":
    main()
