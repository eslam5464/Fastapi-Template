import re
from datetime import datetime
from typing import Annotated

from fastapi import Form
from pydantic import EmailStr, Field, SecretStr, field_validator

from app.core.field_sizes import FieldSizes
from app.schemas import BaseSchema, BaseTimestampSchema

USER_PASSWORD_REGEX = (
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
)
USER_PASSWORD_DESCRIPTION = (
    "Password must be at least 8 characters long, "
    + "contain at least one uppercase letter, "
    + "one lowercase letter, one number, and one special character."
)
USER_USERNAME_REGEX = (
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,50}$"
)
USER_USERNAME_DESCRIPTION = (
    "Username must be 3-50 characters long, "
    + "contain at least one uppercase letter, one lowercase letter, "
    + "one number, and one special character."
)


class UserBase(BaseSchema):
    """Base user schema"""

    username: str
    email: EmailStr
    hashed_password: str
    first_name: str
    last_name: str


class UserCreate(BaseSchema):
    """User creation schema"""

    username: str
    email: EmailStr
    password: str
    first_name: str
    last_name: str


class UserUpdate(BaseSchema):
    """User update schema"""

    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    email: EmailStr | None = None
    password: str | None = None


class UserLogin(BaseSchema):
    """User login schema"""

    email: Annotated[EmailStr, Form()]
    password: Annotated[SecretStr, Form()]


class UserSignup(BaseSchema):
    """User signup schema"""

    username: Annotated[
        str,
        Field(
            min_length=3,
            max_length=FieldSizes.USERNAME,
            description=USER_USERNAME_DESCRIPTION,
        ),
    ] = Form()
    email: Annotated[EmailStr, Form()]
    password: Annotated[
        SecretStr,
        Field(
            min_length=8,
            max_length=FieldSizes.PASSWORD,
            description=USER_PASSWORD_DESCRIPTION,
        ),
    ] = Form()

    @field_validator("username")
    def validate_username(cls, value: str) -> str:
        """Validate username to ensure it contains no spaces."""
        if re.compile(USER_USERNAME_REGEX).match(value) is None:
            raise ValueError(USER_USERNAME_DESCRIPTION)

        return value

    @field_validator("password")
    def validate_password(cls, value: SecretStr) -> SecretStr:
        """Validate password to ensure it meets complexity requirements."""
        if re.compile(USER_PASSWORD_REGEX).match(value.get_secret_value()) is None:
            raise ValueError(USER_PASSWORD_DESCRIPTION)

        return value


class UserForgetPassword(BaseSchema):
    """User reset password schema"""

    email: EmailStr


class UserResponse(UserBase, BaseTimestampSchema):
    """User schema for API response"""

    id: int
    created_at: datetime = Field()
