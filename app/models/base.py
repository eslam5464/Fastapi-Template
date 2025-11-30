import re
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    class_mapper,
    declared_attr,
    mapped_column,
)

from app.core.db import meta


class Base(DeclarativeBase):
    """Base class for all database models"""

    __abstract__ = True

    metadata = meta
    id: Mapped[int] = mapped_column(BigInteger(), autoincrement=True, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()

    def to_dict(
        self,
        exclude_keys: set[str] | None = None,
        exclude_none: bool = False,
    ) -> dict[str, Any]:
        """
        Convert the model instance to a dictionary with only serializable fields.
        """
        exclude_keys = exclude_keys or set()
        serialized_data = {}

        for key in class_mapper(self.__class__).c.keys():
            if key in exclude_keys:
                continue

            value = getattr(self, key)

            if exclude_none and value is None:
                continue

            serialized_data[key] = value

        return serialized_data
