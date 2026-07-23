"""Copier post-generation task: runs in the generated project's directory."""

import shutil
import subprocess
import sys
from pathlib import Path

APPLE_PAY_MARKERS = ("# --- APPLE_PAY_START ---", "# --- APPLE_PAY_END ---")
APPLE_PAY_CI_MARKERS = ("# --- APPLE_PAY_CI_START ---", "# --- APPLE_PAY_CI_END ---")
APPLE_PAY_SETTINGS_MARKERS = (
    "# --- APPLE_PAY_SETTINGS_START ---",
    "# --- APPLE_PAY_SETTINGS_END ---",
)
APPLE_PAY_PROPERTY_MARKERS = (
    "# --- APPLE_PAY_PROPERTY_START ---",
    "# --- APPLE_PAY_PROPERTY_END ---",
)


def strip_marked_block(path: Path, start_marker: str, end_marker: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if start_marker in line), None)
    end = next((i for i, line in enumerate(lines) if end_marker in line), None)
    if start is None or end is None:
        return
    del lines[start : end + 1]
    path.write_text("".join(lines), encoding="utf-8")


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
    if credentials_path.exists():
        strip_marked_block(credentials_path, *APPLE_PAY_MARKERS)
        content = credentials_path.read_text(encoding="utf-8")
        content = content.replace(
            "from pydantic import BaseModel, ConfigDict, Field, model_validator",
            "from pydantic import BaseModel, ConfigDict, model_validator",
        )
        credentials_path.write_text(content, encoding="utf-8")

    config_path = Path("app/core/config.py")
    if config_path.exists():
        content = config_path.read_text(encoding="utf-8")
        content = content.replace(
            "from app.core.credentials import ApplePayStoreCredentials, FirebaseServiceAccount",
            "from app.core.credentials import FirebaseServiceAccount",
        )
        config_path.write_text(content, encoding="utf-8")
        strip_marked_block(config_path, *APPLE_PAY_SETTINGS_MARKERS)
        strip_marked_block(config_path, *APPLE_PAY_PROPERTY_MARKERS)

    ci_path = Path(".github/workflows/ci.yml")
    if ci_path.exists():
        strip_marked_block(ci_path, *APPLE_PAY_CI_MARKERS)


def regenerate_lockfile() -> None:
    try:
        subprocess.run(["uv", "lock"], check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        print(
            f"Warning: could not regenerate uv.lock automatically ({exc}). Run 'uv sync' yourself."
        )


def remove_generate_tooling() -> None:
    # This script only exists to run this task; it has no purpose in a
    # generated project, so it removes its own directory as its last act.
    shutil.rmtree(Path(__file__).resolve().parent, ignore_errors=True)


def git_init_and_commit() -> None:
    try:
        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(
            ["git", "commit", "-m", "chore: initial commit from copier template"],
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        print(
            f"Warning: could not initialize git repository automatically ({exc}). Run 'git init' yourself."
        )


def main() -> None:
    include_apple_pay = len(sys.argv) > 1 and sys.argv[1].strip().lower() == "true"
    if not include_apple_pay:
        remove_apple_pay()

    regenerate_lockfile()
    remove_generate_tooling()
    git_init_and_commit()


if __name__ == "__main__":
    main()
