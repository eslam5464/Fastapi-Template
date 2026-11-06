"""Logout with token revocation (the token blacklist)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from jose import jwt

from app.core.config import settings
from app.models import User
from tests.api.conftest import FakeTokenBlacklist


async def _login(client: AsyncClient, user: User, password: str) -> str:
    response = await client.post("/v1/auth/login", data={"username": user.username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


class TestLogoutRevokesToken:
    """POST /v1/auth/logout puts the access token on the blacklist."""

    @pytest.mark.anyio
    async def test_logout_revokes_token(
        self,
        client: AsyncClient,
        user: User,
        default_password: str,
        fake_token_blacklist: FakeTokenBlacklist,
    ):
        """Test logout reports revoked=True and blacklists the token's jti."""
        access_token = await _login(client, user, default_password)
        jti = jwt.get_unverified_claims(access_token)["jti"]

        response = await client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        assert response.json() == {"message": "Successfully logged out", "revoked": True}
        assert jti in fake_token_blacklist.revoked
        assert fake_token_blacklist.revoked[jti] > 0

    @pytest.mark.anyio
    async def test_token_is_rejected_after_logout(
        self,
        client: AsyncClient,
        user: User,
        default_password: str,
    ):
        """Test the same access token gets 401 once the user has logged out."""
        access_token = await _login(client, user, default_password)
        headers = {"Authorization": f"Bearer {access_token}"}

        assert (await client.get("/v1/users/me", headers=headers)).status_code == 200
        assert (await client.post("/v1/auth/logout", headers=headers)).status_code == 200

        response = await client.get("/v1/users/me", headers=headers)

        assert response.status_code == 401, f"Response: {response.text}"
        assert "revoked" in response.json()["detail"].lower()

    @pytest.mark.anyio
    async def test_logout_token_without_jti(
        self,
        client: AsyncClient,
        user: User,
    ):
        """Test logout fails when token doesn't have jti claim."""
        # Create token without jti
        token_no_jti = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) + timedelta(hours=1),
                "iat": datetime.now(UTC),
                "type": "access",
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        response = await client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {token_no_jti}"},
        )

        assert response.status_code == 401, f"Response: {response.text}"
        data = response.json()
        assert "Invalid token format" in data["detail"]

    @pytest.mark.anyio
    async def test_logout_internal_error(
        self,
        client: AsyncClient,
        user: User,
        default_password: str,
        fake_token_blacklist: FakeTokenBlacklist,
    ):
        """Test logout handles internal errors gracefully."""
        # First login to get tokens
        login_response = await client.post(
            "/v1/auth/login",
            data={
                "username": user.username,
                "password": default_password,
            },
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        access_token = token_data["access_token"]

        # Make revoking the token fail
        fake_token_blacklist.revoke_token = AsyncMock(side_effect=Exception("Database error"))

        response = await client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 500, f"Response: {response.text}"
        data = response.json()
        assert "Logout failed" in data["detail"]


class TestTokenRevocationIntegration:
    """Integration tests for token revocation flow."""

    @pytest.mark.anyio
    async def test_revoked_access_token_cannot_be_used(
        self,
        client: AsyncClient,
        user: User,
        default_password: str,
    ):
        """Test that a revoked access token is rejected on subsequent requests."""
        # Login to get tokens
        login_response = await client.post(
            "/v1/auth/login",
            data={
                "username": user.username,
                "password": default_password,
            },
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        access_token = token_data["access_token"]

        # Mock token_blacklist for logout (auth_service for auth + endpoint for revoke)
        with patch("app.services.auth_service.token_blacklist") as mock_auth_blacklist:
            mock_auth_blacklist.is_revoked = AsyncMock(return_value=False)
            mock_auth_blacklist.get_user_revocation_time = AsyncMock(return_value=None)
            with patch("app.api.v1.endpoints.auth.token_blacklist") as mock_blacklist:
                mock_blacklist.revoke_token = AsyncMock(return_value=True)

                # Logout
                logout_response = await client.post(
                    "/v1/auth/logout",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                assert logout_response.status_code == 200

        # Mock token_blacklist to return True for is_revoked (token is blacklisted)
        with patch("app.services.auth_service.token_blacklist") as mock_blacklist:
            mock_blacklist.is_revoked = AsyncMock(return_value=True)
            mock_blacklist.get_user_revocation_time = AsyncMock(return_value=None)

            # Try to use the revoked token
            response = await client.get(
                "/v1/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert response.status_code == 401, f"Response: {response.text}"
            data = response.json()
            assert "revoked" in data["detail"].lower()

    @pytest.mark.anyio
    async def test_user_revocation_time_rejects_old_tokens(
        self,
        client: AsyncClient,
        user: User,
        default_password: str,
    ):
        """Test that tokens issued before user revocation time are rejected."""
        # Login to get tokens
        login_response = await client.post(
            "/v1/auth/login",
            data={
                "username": user.username,
                "password": default_password,
            },
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        access_token = token_data["access_token"]

        # Mock token_blacklist to return a revocation time in the future of token's iat
        with patch("app.services.auth_service.token_blacklist") as mock_blacklist:
            mock_blacklist.is_revoked = AsyncMock(return_value=False)
            # Set revocation time to now (after token was issued)
            mock_blacklist.get_user_revocation_time = AsyncMock(return_value=int(datetime.now(UTC).timestamp()) + 1)

            # Try to use the token
            response = await client.get(
                "/v1/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert response.status_code == 401, f"Response: {response.text}"
            data = response.json()
            assert "revoked" in data["detail"].lower()
