from typing import Sequence

from app.models.item import Item
from app.repos.item import ItemRepo
from app.schemas.item import ItemCreate, ItemUpdate
from app.services.exceptions.base import DuplicateResourceError, ResourceNotFoundError


class ItemService:
    """
    Business rules for items: an example of a service in this architecture.
    Receives ItemRepo via constructor — never sees database sessions.

    Raises service exceptions (ResourceNotFoundError, DuplicateResourceError)
    which the API layer translates to HTTP exceptions.
    """

    def __init__(self, item_repo: ItemRepo):
        self.item_repo = item_repo

    async def list_items(self, skip: int = 0, limit: int = 50) -> Sequence[Item]:
        """
        List one page of items, oldest first.

        Args:
            skip: Number of items to skip.
            limit: Maximum number of items to return.

        Returns:
            The items of the page.
        """
        return await self.item_repo.get_page(skip=skip, limit=limit)

    async def get_item(self, item_id: int) -> Item:
        """
        Get one item.

        Args:
            item_id: The ID of the item.

        Returns:
            The item.

        Raises:
            ResourceNotFoundError: If no item has this ID.
        """
        item = await self.item_repo.get_by_id(item_id)
        if item is None:
            raise ResourceNotFoundError(f"Item {item_id} was not found.")

        return item

    async def create_item(self, data: ItemCreate) -> Item:
        """
        Create an item. Names are unique.

        Args:
            data: The data of the new item.

        Returns:
            The created item.

        Raises:
            DuplicateResourceError: If an item with this name already exists.
        """
        if await self.item_repo.get_by_name(data.name) is not None:
            raise DuplicateResourceError(f"An item named '{data.name}' already exists.")

        return await self.item_repo.create_one(data)

    async def update_item(self, item_id: int, data: ItemUpdate) -> Item:
        """
        Change the given fields of an item. Fields left out keep their value.

        Args:
            item_id: The ID of the item.
            data: The fields to change.

        Returns:
            The updated item.

        Raises:
            ResourceNotFoundError: If no item has this ID.
            DuplicateResourceError: If another item already has the new name.
        """
        item = await self.get_item(item_id)
        if not data.model_dump(exclude_none=True):
            return item

        if data.name is not None and data.name != item.name:
            if await self.item_repo.get_by_name(data.name) is not None:
                raise DuplicateResourceError(f"An item named '{data.name}' already exists.")

        updated = await self.item_repo.update_by_id(item_id, data)
        if updated is None:
            raise ResourceNotFoundError(f"Item {item_id} was not found.")

        return updated

    async def delete_item(self, item_id: int) -> None:
        """
        Delete an item.

        Args:
            item_id: The ID of the item.

        Raises:
            ResourceNotFoundError: If no item has this ID.
        """
        if not await self.item_repo.delete_by_id(item_id):
            raise ResourceNotFoundError(f"Item {item_id} was not found.")
