from app.schemas.base import BaseSchema


class HealthCheckResponse(BaseSchema):
    """Schema for health check response"""

    status: str
