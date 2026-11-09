# --- SNAPSHOT NOTICE (fastapi-template-architect skill) ---
# Copy of app/services/exceptions/base.py from eslam5464/Fastapi-Template, taken 2026-11-09,
# with every optional service included (a generated project only has the
# services chosen for it). The real repo is the source of truth; this is a
# fallback/reference copy for offline scaffolding and Extend/Audit-mode
# pattern-matching. Prefer driving the real Copier template
# (see references/copier-template-mechanics.md) whenever that's available.
# --- END SNAPSHOT NOTICE ---


class ServiceException(Exception):
    """Base exception for service layer errors."""
