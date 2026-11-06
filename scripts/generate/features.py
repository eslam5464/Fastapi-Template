"""Feature manifest for the marker engine (scripts/generate/markers.py).

Describes every optional feature the Copier template knows about: its marker
tag, the Copier question that toggles it, its third-party imports, and the
repo-relative paths that only exist when the feature is on.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Feature:
    """One optional feature of the generated project.

    Attributes:
        name: Marker tag used in ``FEATURE[<expr>]`` marker expressions.
        question: Copier question name that toggles the feature, or None for
            reserved/computed features that have no question.
        parent: Feature this one depends on; a child may only be on when its
            parent is on, or None.
        computed_from: Feature names this feature is derived from. A computed
            feature has no question and is on when any listed feature is on.
        imports: Third-party top-level module names the feature may import.
        forbidden: Regex strings that must not appear in a bake when the
            feature is off.
    """

    name: str
    question: str | None = None
    parent: str | None = None
    computed_from: tuple[str, ...] = ()
    imports: tuple[str, ...] = ()
    forbidden: tuple[str, ...] = ()


FEATURES: tuple[Feature, ...] = (
    # Reserved: the template repository itself. Never a question - always off
    # when generating a project.
    Feature("_template"),
    Feature(
        "gcs",
        question="include_gcs",
        imports=("gcloud", "aiofiles"),
        forbidden=(r"gcloud", r"aiofiles", r"google_bucket", r"gcs_exceptions", r"\b[Gg][Cc][Ss]\b"),
    ),
    Feature(
        "backblaze",
        question="include_backblaze",
        imports=("b2sdk",),
        forbidden=(r"b2sdk", r"BackBlaze", r"back_blaze"),
    ),
    Feature(
        "apple_pay",
        question="include_apple_pay",
        imports=("appstoreserverlibrary", "cryptography"),
        forbidden=(r"appstoreserverlibrary", r"ApplePay"),
    ),
)

FEATURES_BY_NAME: dict[str, Feature] = {feature.name: feature for feature in FEATURES}

# Repo-relative path -> keep-expression (same expression syntax as markers).
# A key ending in "/" is a directory (deleted with its whole tree when the
# expression is false). Every key must exist in the template repository.
PATHS: dict[str, str] = {
    "app/services/gcs.py": "gcs",
    "app/core/exceptions/gcs_exceptions.py": "gcs",
    "app/schemas/google_bucket.py": "gcs",
    "tests/services/gcs/": "gcs",
    "docs/integrations/gcs.md": "gcs",
    "app/services/back_blaze_b2.py": "backblaze",
    "app/core/exceptions/back_blaze_exceptions.py": "backblaze",
    "app/schemas/back_blaze_bucket.py": "backblaze",
    "tests/services/backblaze/": "backblaze",
    "docs/integrations/backblaze.md": "backblaze",
    "app/services/payments/": "apple_pay",
    "app/core/exceptions/apple_pay.py": "apple_pay",
    "app/core/credentials/apple_pay.py": "apple_pay",
    "tests/services/payments/": "apple_pay",
    "tests/apple_pay_credentials.py": "apple_pay",
}

# Third-party top-level modules every generated project may import (checked by
# check_variants.py). Services that are not toggleable features yet still live
# here; making a service a Feature moves its modules into that Feature.imports.
BASE_IMPORTS: tuple[str, ...] = (
    "alembic",
    "anyio",
    "brevo",
    "celery",
    "faker",
    "fastapi",
    "firebase_admin",
    "google",
    "gunicorn",
    "httpx",
    "jose",
    "loguru",
    "pwdlib",
    "pydantic",
    "pydantic_settings",
    "redis",
    "resend",
    "sqlalchemy",
    "starlette",
    "uvicorn",
    "yarl",
)

# Extra third-party modules allowed only under tests/ (the test dependency group).
TEST_IMPORTS: tuple[str, ...] = ("anyio", "faker", "httpx", "pytest")

# Repo-relative prefixes (forward slashes) that are never scanned for markers.
SCAN_EXCLUDE: tuple[str, ...] = (
    ".git/",
    "scripts/generate/",
    "uv.lock",
    ".venv/",
    "htmlcov/",
    ".claude/skills/fastapi-template-architect/references/",
    ".agents/skills/fastapi-template-architect/references/",
)
