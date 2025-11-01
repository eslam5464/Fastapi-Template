import uuid

from pydantic import field_validator

from app.schemas import BaseSchema


class Token(BaseSchema):
    """Token response schema"""

    access_token: str
    token_type: str = "Bearer"
    refresh_token: str | None = None

    def __str__(self):
        return self.token_type + " " + self.access_token


class TokenData(BaseSchema):
    """Token data schema parsed from JWT payload"""

    user_id: int | str | uuid.UUID
    issued_at: int | None = None
    expires_at: int | None = None

    @field_validator("user_id")
    @classmethod
    def parse_uuid(cls, v: str | int | uuid.UUID) -> str | int:
        if isinstance(v, uuid.UUID):
            return str(v)

        return v


class TokenPayload(BaseSchema):
    """Token payload for refresh token"""

    refresh_token: str
