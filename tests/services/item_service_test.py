import pytest
from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from app.repos.item import ItemRepo
from app.schemas.item import ItemCreate, ItemUpdate
from app.services.exceptions.base import DuplicateResourceError, ResourceNotFoundError
from app.services.item_service import ItemService

MISSING_ID = 999999999


@pytest.fixture
def item_service(db_session: AsyncSession) -> ItemService:
    return ItemService(item_repo=ItemRepo(db_session))


@pytest.mark.anyio
class TestItemService:
    async def test_create_and_get(self, item_service: ItemService, faker: Faker):
        name = faker.unique.word()

        created = await item_service.create_item(ItemCreate(name=name, description="A thing"))
        fetched = await item_service.get_item(created.id)

        assert fetched.id == created.id
        assert fetched.name == name
        assert fetched.description == "A thing"
        assert fetched.is_active is True

    async def test_create_rejects_a_duplicate_name(self, item_service: ItemService, faker: Faker):
        name = faker.unique.word()
        await item_service.create_item(ItemCreate(name=name))

        with pytest.raises(DuplicateResourceError):
            await item_service.create_item(ItemCreate(name=name))

    async def test_get_missing_item(self, item_service: ItemService):
        with pytest.raises(ResourceNotFoundError):
            await item_service.get_item(MISSING_ID)

    async def test_list_is_paged_and_ordered(self, item_service: ItemService, faker: Faker):
        created = [await item_service.create_item(ItemCreate(name=faker.unique.word())) for _ in range(3)]

        first_two = await item_service.list_items(skip=0, limit=2)
        rest = await item_service.list_items(skip=2, limit=2)

        assert [item.id for item in first_two] == [created[0].id, created[1].id]
        assert [item.id for item in rest] == [created[2].id]

    async def test_update_changes_only_the_given_fields(self, item_service: ItemService, faker: Faker):
        created = await item_service.create_item(ItemCreate(name=faker.unique.word(), description="before"))

        updated = await item_service.update_item(created.id, ItemUpdate(is_active=False))

        assert updated.is_active is False
        assert updated.name == created.name
        assert updated.description == "before"

    async def test_update_without_fields_returns_the_item(self, item_service: ItemService, faker: Faker):
        created = await item_service.create_item(ItemCreate(name=faker.unique.word()))

        unchanged = await item_service.update_item(created.id, ItemUpdate())

        assert unchanged.id == created.id
        assert unchanged.name == created.name

    async def test_update_rejects_a_name_taken_by_another_item(self, item_service: ItemService, faker: Faker):
        first = await item_service.create_item(ItemCreate(name=faker.unique.word()))
        second = await item_service.create_item(ItemCreate(name=faker.unique.word()))

        with pytest.raises(DuplicateResourceError):
            await item_service.update_item(second.id, ItemUpdate(name=first.name))

    async def test_update_accepts_the_item_keeping_its_own_name(self, item_service: ItemService, faker: Faker):
        created = await item_service.create_item(ItemCreate(name=faker.unique.word()))

        updated = await item_service.update_item(created.id, ItemUpdate(name=created.name, description="new"))

        assert updated.description == "new"

    async def test_update_missing_item(self, item_service: ItemService):
        with pytest.raises(ResourceNotFoundError):
            await item_service.update_item(MISSING_ID, ItemUpdate(is_active=False))

    async def test_delete(self, item_service: ItemService, faker: Faker):
        created = await item_service.create_item(ItemCreate(name=faker.unique.word()))

        await item_service.delete_item(created.id)

        with pytest.raises(ResourceNotFoundError):
            await item_service.get_item(created.id)

    async def test_delete_missing_item(self, item_service: ItemService):
        with pytest.raises(ResourceNotFoundError):
            await item_service.delete_item(MISSING_ID)
