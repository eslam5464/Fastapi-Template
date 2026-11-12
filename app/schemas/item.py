from typing import Annotated

from pydantic import Field

from app.core.constants import FieldSizes
from app.schemas.base import BaseSchema, BaseTimestampSchema


class ItemCreate(BaseSchema):
    """Data needed to create an item"""

    name: Annotated[str, Field(min_length=1, max_length=FieldSizes.MEDIUM)]
    description: Annotated[str | None, Field(max_length=FieldSizes.LONG)] = None
    is_active: bool = True


class ItemUpdate(BaseSchema):
    """Fields of an item that can change; a field left out keeps its value"""

    name: Annotated[str | None, Field(min_length=1, max_length=FieldSizes.MEDIUM)] = None
    description: Annotated[str | None, Field(max_length=FieldSizes.LONG)] = None
    is_active: bool | None = None


class ItemResponse(BaseTimestampSchema):
    """Item schema for API responses"""

    id: int
    name: str
    description: str | None
    is_active: bool
