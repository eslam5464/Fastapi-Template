from typing import AsyncGenerator

import pytest
from faker import Faker
from fastapi import status
from httpx import AsyncClient

# --- FEATURE[auth] START ---
from app.api.v1.deps.auth import get_current_user
from app.main import v1_app

# --- FEATURE[auth] END ---
# --- FEATURE[csrf] START ---
from app.middleware.csrf import CSRF_COOKIE_NAME, CSRF_HEADER_NAME

# --- FEATURE[csrf] END ---

MISSING_ID = 999999999


@pytest.fixture
async def items_client(client: AsyncClient) -> AsyncGenerator[AsyncClient, None]:
    """The test client, allowed to call the items routes."""
    # --- FEATURE[auth] START ---
    # The items routes need a logged-in user. These tests are about the CRUD
    # behaviour, so they skip the login check (items_auth_test.py covers it).
    # The test_app fixture clears the override again.
    v1_app.dependency_overrides[get_current_user] = lambda: None
    # --- FEATURE[auth] END ---
    # --- FEATURE[csrf] START ---
    # State-changing requests must echo the CSRF cookie in a header.
    client.cookies.set(CSRF_COOKIE_NAME, "test-csrf-token")
    client.headers[CSRF_HEADER_NAME] = "test-csrf-token"
    # --- FEATURE[csrf] END ---
    yield client


@pytest.mark.anyio
class TestItemsEndpoints:
    async def test_create_item(self, items_client: AsyncClient, faker: Faker):
        name = faker.unique.word()

        response = await items_client.post("/v1/items", json={"name": name, "description": "A thing"})

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["name"] == name
        assert body["description"] == "A thing"
        assert body["is_active"] is True
        assert body["id"] > 0
        assert "created_at" in body

    async def test_create_item_with_a_duplicate_name(self, items_client: AsyncClient, faker: Faker):
        name = faker.unique.word()
        await items_client.post("/v1/items", json={"name": name})

        response = await items_client.post("/v1/items", json={"name": name})

        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_create_item_with_invalid_data(self, items_client: AsyncClient):
        response = await items_client.post("/v1/items", json={"name": ""})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_read_item(self, items_client: AsyncClient, faker: Faker):
        created = (await items_client.post("/v1/items", json={"name": faker.unique.word()})).json()

        response = await items_client.get(f"/v1/items/{created['id']}")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == created

    async def test_read_missing_item(self, items_client: AsyncClient):
        response = await items_client.get(f"/v1/items/{MISSING_ID}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_list_items(self, items_client: AsyncClient, faker: Faker):
        names = [faker.unique.word() for _ in range(3)]
        for name in names:
            await items_client.post("/v1/items", json={"name": name})

        response = await items_client.get("/v1/items", params={"skip": 1, "limit": 2})

        assert response.status_code == status.HTTP_200_OK
        assert [item["name"] for item in response.json()] == names[1:]

    async def test_list_items_rejects_a_limit_over_the_maximum(self, items_client: AsyncClient):
        response = await items_client.get("/v1/items", params={"limit": 101})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_update_item(self, items_client: AsyncClient, faker: Faker):
        created = (await items_client.post("/v1/items", json={"name": faker.unique.word()})).json()

        response = await items_client.patch(f"/v1/items/{created['id']}", json={"is_active": False})

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["is_active"] is False
        assert body["name"] == created["name"]

    async def test_update_item_to_a_taken_name(self, items_client: AsyncClient, faker: Faker):
        first = (await items_client.post("/v1/items", json={"name": faker.unique.word()})).json()
        second = (await items_client.post("/v1/items", json={"name": faker.unique.word()})).json()

        response = await items_client.patch(f"/v1/items/{second['id']}", json={"name": first["name"]})

        assert response.status_code == status.HTTP_409_CONFLICT

    async def test_update_missing_item(self, items_client: AsyncClient):
        response = await items_client.patch(f"/v1/items/{MISSING_ID}", json={"is_active": False})

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_item(self, items_client: AsyncClient, faker: Faker):
        created = (await items_client.post("/v1/items", json={"name": faker.unique.word()})).json()

        response = await items_client.delete(f"/v1/items/{created['id']}")

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert (await items_client.get(f"/v1/items/{created['id']}")).status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_missing_item(self, items_client: AsyncClient):
        response = await items_client.delete(f"/v1/items/{MISSING_ID}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
