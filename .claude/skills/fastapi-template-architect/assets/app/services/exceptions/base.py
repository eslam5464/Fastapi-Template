# --- SNAPSHOT NOTICE (fastapi-template-architect skill) ---
# Verbatim copy of app/services/exceptions/base.py from eslam5464/Fastapi-Template, taken 2026-08-30.
# The real repo is the source of truth; this is a fallback/reference copy
# for offline scaffolding and Extend/Audit-mode pattern-matching. It can drift
# from the live repo over time - prefer driving the real Copier template
# (see references/copier-template-mechanics.md) whenever that's available.
# --- END SNAPSHOT NOTICE ---

class ServiceException(Exception):
    """Base exception for service layer errors."""
