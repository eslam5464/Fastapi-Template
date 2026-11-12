"""The items routes need a logged-in user when the project has authentication."""

import pytest
from fastapi import status
from httpx import AsyncClient

from app.schemas import Token


@pytest.mark.anyio
class TestItemsNeedLogin:
    async def test_list_without_a_token_is_rejected(self, client: AsyncClient):
        response = await client.get("/v1/items")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_read_without_a_token_is_rejected(self, client: AsyncClient):
        response = await client.get("/v1/items/1")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_list_with_a_token_is_allowed(self, client: AsyncClient, token: Token):
        response = await client.get("/v1/items", headers={"Authorization": f"Bearer {token.access_token}"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []
