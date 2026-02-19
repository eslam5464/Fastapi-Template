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

        Args:
            exclude_keys (set[str], optional): A set of field names to exclude from the resulting dictionary. Defaults to None.
            exclude_none (bool, optional): If True, fields with None values will be excluded from the resulting dictionary. Defaults to False.

        Returns:
            serialized_data (dict[str, Any]): A dictionary representation of the model instance with only serializable fields.
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

    @classmethod
    def get_schema(cls) -> Optional[str]:
        """
        Get the schema name for the model.

        Returns:
            schema_name (str | None): The schema name if available, otherwise None.
        """
        return cls.metadata.schema if cls.metadata else None

    @classmethod
    def get_table_name(cls) -> Optional[str]:
        """
        Get the table name for the model.

        Returns:
            table_name (str | None): The table name if available, otherwise None.
        """
        return cls.__tablename__ if hasattr(cls, "__tablename__") else None

    @classmethod
    def dict_keys(cls) -> set[str]:
        """
        Get the set of column keys for the model.

        Returns:
            keys (set[str]): A set of column keys for the model.
        """
        return set(class_mapper(cls).c.keys())

    def __repr__(self) -> str:
        """
        Get the string representation of the model instance.

        Returns:
            repr_str (str): The string representation of the model instance.
        """
        return f"<{self.__class__.__name__}(id={self.id})>"
