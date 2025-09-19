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
