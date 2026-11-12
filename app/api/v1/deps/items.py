from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.repos.item import ItemRepo
from app.services.item_service import ItemService


def get_item_service(db: Annotated[AsyncSession, Depends(get_session)]) -> ItemService:
    """Dependency provider for ItemService — the single place ItemService is constructed."""
    return ItemService(item_repo=ItemRepo(db))
