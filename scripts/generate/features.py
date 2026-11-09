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
        doc_forbidden: Extra regex strings checked only in the prose docs
            (README.md, docs/), for wording the code tokens don't cover
            (e.g. "Apple Pay", or links to the feature's integration guide).
    """

    name: str
    question: str | None = None
    parent: str | None = None
    computed_from: tuple[str, ...] = ()
    imports: tuple[str, ...] = ()
    forbidden: tuple[str, ...] = ()
    doc_forbidden: tuple[str, ...] = ()


FEATURES: tuple[Feature, ...] = (
    # Reserved: the template repository itself. Never a question - always off
    # when generating a project.
    Feature("_template"),
    Feature(
        "redis_cache",
        question="include_redis_cache",
        forbidden=(
            r"cache_manager",
            r"CacheManager",
            r"cache_result",
            r"\bcache_enabled\b",
            r"cache_ttl_",
            r"CACHE_(ENABLED|TTL)",
        ),
        doc_forbidden=(
            r"integrations/caching",
            r"(?i)redis cache",
        ),
    ),
    Feature(
        "redis_rate_limit",
        question="include_redis_rate_limit",
        forbidden=(
            r"rate_limiter",
            r"\bRateLimiter\b",
            r"RateLimitPrefix",
            r"RateLimitInfoDict",
            r"RateLimitHeaderMiddleware",
            r"RATE_LIMIT_",
            r"\brate_limit_\w+",
            r"deps\.rate_limit\b",
        ),
        doc_forbidden=(r"integrations/rate-limiting", r"X-RateLimit"),
    ),
    Feature(
        "redis_token_blacklist",
        question="include_redis_token_blacklist",
        forbidden=(r"token_blacklist", r"TokenBlacklist"),
        doc_forbidden=(r"integrations/token-revocation",),
    ),
    Feature(
        "celery",
        question="include_celery",
        imports=("celery", "faker"),
        forbidden=(r"(?i)celery", r"psycopg", r"db_sync", r"db_url_sync", r"task_queue", r"(?i)data_seeding"),
        doc_forbidden=(r"integrations/celery",),
    ),
    # Computed: on when any Redis-backed service is chosen. Listed after its
    # sources, since post_gen.resolve() computes features in manifest order.
    Feature(
        "redis",
        computed_from=("redis_cache", "redis_rate_limit", "redis_token_blacklist", "celery"),
        imports=("redis",),
        forbidden=(r"(?i)redis",),
    ),
    Feature(
        "firebase",
        question="include_firebase",
        imports=("firebase_admin",),
        forbidden=(r"(?i)firebase",),
        doc_forbidden=(r"integrations/firebase",),
    ),
    Feature(
        "firestore",
        question="include_firestore",
        parent="firebase",
        imports=("google",),
        forbidden=(r"(?i)firestore",),
        doc_forbidden=(r"integrations/firestore",),
    ),
    Feature(
        "gcs",
        question="include_gcs",
        imports=("gcloud", "aiofiles"),
        forbidden=(r"gcloud[.-]", r"aiofiles", r"google_bucket", r"gcs_exceptions", r"\b[Gg][Cc][Ss]\b"),
        doc_forbidden=(
            r"integrations/gcs",
            r"(?i)google cloud storage",
        ),
    ),
    Feature(
        "backblaze",
        question="include_backblaze",
        imports=("b2sdk",),
        forbidden=(r"b2sdk", r"BackBlaze", r"back_blaze"),
        doc_forbidden=(
            r"integrations/backblaze",
            r"(?i)backblaze",
        ),
    ),
    Feature(
        "resend",
        question="include_resend",
        imports=("resend",),
        forbidden=(r"(?i)resend",),
    ),
    Feature(
        "brevo",
        question="include_brevo",
        imports=("brevo",),
        forbidden=(r"(?i)brevo",),
    ),
    Feature(
        "openobserve",
        question="include_openobserve",
        imports=("httpx",),
        forbidden=(r"(?i)openobserve",),
        doc_forbidden=(r"integrations/openobserve",),
    ),
    Feature(
        "apple_pay",
        question="include_apple_pay",
        imports=("appstoreserverlibrary", "cryptography"),
        forbidden=(r"appstoreserverlibrary", r"ApplePay", r"(?i)apple_pay"),
        doc_forbidden=(
            r"integrations/apple-pay",
            r"(?i)apple pay",
        ),
    ),
)

FEATURES_BY_NAME: dict[str, Feature] = {feature.name: feature for feature in FEATURES}

# Repo-relative path -> keep-expression (same expression syntax as markers).
# A key ending in "/" is a directory (deleted with its whole tree when the
# expression is false). Every key must exist in the template repository.
PATHS: dict[str, str] = {
    # The skill's eval prompts test the template itself: template repo only.
    ".claude/skills/fastapi-template-architect/evals/": "_template",
    # The Archify diagram of the template itself (every service on): template repo only.
    "docs/architecture/fastapi-template.architecture.html": "_template",
    "docs/architecture/fastapi-template.architecture.json": "_template",
    "docs/architecture/fastapi-template.architecture.visual-check.html": "_template",
    "docs/architecture/fastapi-template.architecture.visual-check.json": "_template",
    "docs/architecture/fastapi-template.architecture.visual-check.1440x900.dark.png": "_template",
    "docs/architecture/fastapi-template.architecture.visual-check.1440x900.light.png": "_template",
    "docs/architecture/fastapi-template.architecture.visual-check.2048x1320.dark.png": "_template",
    "docs/architecture/fastapi-template.architecture.visual-check.2048x1320.light.png": "_template",
    "app/services/cache/": "redis",
    "app/services/cache/manager.py": "redis_cache",
    "app/services/cache/decorators.py": "redis_cache",
    "tests/services/cache/": "redis",
    "tests/services/cache/manager_test.py": "redis_cache",
    "tests/services/cache/decorators_test.py": "redis_cache",
    "tests/main_cache_test.py": "redis_cache",
    "tests/services/payments/apple_pay_cache_test.py": "apple_pay&redis_cache",
    "docs/integrations/caching.md": "redis_cache",
    "app/services/cache/token_blacklist.py": "redis_token_blacklist",
    "tests/services/cache/token_blacklist_test.py": "redis_token_blacklist",
    "tests/main_token_blacklist_test.py": "redis_token_blacklist",
    "tests/api/conftest.py": "redis_token_blacklist",
    "tests/api/v1/deps/token_revocation_test.py": "redis_token_blacklist",
    "tests/api/v1/endpoints/logout_revocation_test.py": "redis_token_blacklist",
    "docs/integrations/token-revocation.md": "redis_token_blacklist",
    "app/services/cache/rate_limiter.py": "redis_rate_limit",
    "app/core/exceptions/rate_limiter.py": "redis_rate_limit",
    "app/core/types.py": "redis_rate_limit",
    "app/api/v1/deps/rate_limit.py": "redis_rate_limit",
    "app/middleware/rate_limit.py": "redis_rate_limit",
    "tests/services/cache/rate_limiter_test.py": "redis_rate_limit",
    "tests/api/v1/deps/rate_limit_part1_test.py": "redis_rate_limit",
    "tests/api/v1/deps/rate_limit_part2_test.py": "redis_rate_limit",
    "tests/api/v1/endpoints/rate_limit_wiring_test.py": "redis_rate_limit",
    "tests/main_rate_limit_test.py": "redis_rate_limit",
    "docs/integrations/rate-limiting.md": "redis_rate_limit",
    "app/services/task_queue/": "celery",
    "app/core/db_sync.py": "celery",
    "tests/services/task_queue/": "celery",
    "tests/core/db_sync_test.py": "celery",
    "scripts/celery_beat.sh": "celery",
    "scripts/celery_beat.bat": "celery",
    "scripts/celery_worker.sh": "celery",
    "scripts/celery_worker.bat": "celery",
    "docs/integrations/celery.md": "celery",
    "app/core/openobserve.py": "openobserve",
    "tests/core/openobserve_test.py": "openobserve",
    "docs/integrations/openobserve.md": "openobserve",
    "app/services/email/": "resend|brevo",
    "app/services/email/resend.py": "resend",
    "app/services/email/brevo.py": "brevo",
    "app/services/exceptions/email.py": "resend|brevo",
    "app/services/types/email.py": "resend|brevo",
    "tests/services/email/": "resend|brevo",
    "tests/services/email/resend_test.py": "resend",
    "tests/services/email/brevo_test.py": "brevo",
    "docs/integrations/email.md": "resend|brevo",
    "app/services/firebase.py": "firebase",
    "app/core/credentials/firebase.py": "firebase",
    "app/core/exceptions/firebase_exceptions.py": "firebase",
    "app/schemas/firebase.py": "firebase",
    "tests/services/firebase/": "firebase",
    "docs/integrations/firebase.md": "firebase",
    "app/services/firestore.py": "firestore",
    "tests/services/firebase/firestore_test.py": "firestore",
    "docs/integrations/firestore.md": "firestore",
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
    "docs/integrations/apple-pay.md": "apple_pay",
}

# Third-party top-level modules every generated project may import (checked by
# check_variants.py). Services that are not toggleable features yet still live
# here; making a service a Feature moves its modules into that Feature.imports.
BASE_IMPORTS: tuple[str, ...] = (
    "alembic",
    "anyio",
    "fastapi",
    "gunicorn",
    "jose",
    "loguru",
    "pwdlib",
    "pydantic",
    "pydantic_settings",
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
