# --- SNAPSHOT NOTICE (fastapi-template-architect skill) ---
# Verbatim copy of app/schemas/base.py from eslam5464/Fastapi-Template, taken 2026-08-30.
# The real repo is the source of truth; this is a fallback/reference copy
# for offline scaffolding and Extend/Audit-mode pattern-matching. It can drift
# from the live repo over time - prefer driving the real Copier template
# (see references/copier-template-mechanics.md) whenever that's available.
# --- END SNAPSHOT NOTICE ---

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration"""

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        extra="forbid",
    )


class BaseTimestampSchema(BaseSchema):
    """Base schema with timestamp fields"""

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        extra="forbid",
    )
    created_at: datetime
    updated_at: datetime | None = None
