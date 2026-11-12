from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.repos.base import BaseRepository
from app.schemas.item import ItemCreate, ItemUpdate


class ItemRepo(BaseRepository[Item, ItemCreate, ItemUpdate]):
    def __init__(self, session: AsyncSession):
        """Item repository for database operations"""
        super().__init__(session, Item)

    async def get_by_name(self, name: str) -> Item | None:
        """
        Get an item by its name

        Args:
            name (str): The name of the item.

        Returns:
            Item | None: The item if found, else None.
        """
        query = select(self.model).where(self.model.name == name)
        result = await self.session.execute(query)

        return result.scalar_one_or_none()

    async def get_page(self, skip: int = 0, limit: int = 50) -> Sequence[Item]:
        """
        Get one page of items, oldest first

        Args:
            skip (int): Number of items to skip.
            limit (int): Maximum number of items to return.

        Returns:
            Sequence[Item]: The items of the page.
        """
        query = select(self.model).order_by(self.model.id).offset(skip).limit(limit)
        result = await self.session.execute(query)

        return result.scalars().all()
