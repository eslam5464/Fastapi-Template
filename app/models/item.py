from sqlalchemy import Boolean, String, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import FieldSizes
from app.models.base import Base


class Item(Base):
    """Example domain model: a named item that can be switched off."""

    name: Mapped[str] = mapped_column(
        String(FieldSizes.MEDIUM),
        unique=True,
        index=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        String(FieldSizes.LONG),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean(),
        server_default=true(),
        nullable=False,
    )
