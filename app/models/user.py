from typing import Optional

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import FieldSizes
from app.models.base import Base


class User(Base):
    """User model"""

    username: Mapped[str] = mapped_column(
        String(FieldSizes.USERNAME),
        unique=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(FieldSizes.EMAIL),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(FieldSizes.PASSWORD_HASH),
        nullable=False,
    )
    first_name: Mapped[Optional[str]] = mapped_column(
        String(FieldSizes.FIRST_NAME),
        nullable=False,
    )
    last_name: Mapped[Optional[str]] = mapped_column(
        String(FieldSizes.LAST_NAME),
        nullable=False,
    )
