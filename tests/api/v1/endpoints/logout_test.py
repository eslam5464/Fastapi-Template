"""Tests for the logout endpoint and token revocation."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from jose import jwt

from app.core.config import settings
from app.models import User


class TestLogoutEndpoint:
    """Test suite for POST /api/v1/auth/logout endpoint."""

    @pytest.mark.anyio
    async def test_logout_success(
        self,
        client: AsyncClient,
        user: User,
        default_password: str,
    ):
        """Test successful logout with valid access token."""
        # First login to get tokens
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": user.username,
                "password": default_password,
            },
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        access_token = token_data["access_token"]

        # Mock the token blacklist
        with patch("app.api.v1.endpoints.auth.token_blacklist") as mock_blacklist:
            mock_blacklist.revoke_token = AsyncMock(return_value=True)

            # Logout
            response = await client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Successfully logged out"
            assert data["revoked"] is True

            # Verify revoke_token was called
            mock_blacklist.revoke_token.assert_called_once()

    @pytest.mark.anyio
    async def test_logout_invalid_token(
        self,
        client: AsyncClient,
    ):
        """Test logout fails with invalid token."""
        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer invalid.token.here"},
        )

        assert response.status_code == 401
        data = response.json()
        assert "Could not validate credentials" in data["detail"]

    @pytest.mark.anyio
    async def test_logout_expired_token(
        self,
        client: AsyncClient,
        user: User,
    ):
        """Test logout fails with expired token."""
        # Create an expired token
        expired_token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) - timedelta(hours=1),
                "iat": datetime.now(UTC) - timedelta(hours=2),
                "type": "access",
                "jti": str(uuid.uuid4()),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_logout_no_token(
        self,
        client: AsyncClient,
    ):
        """Test logout fails without authorization header."""
        response = await client.post("/api/v1/auth/logout")

        assert response.status_code == 401

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

        # Mock both get_current_user (to pass auth) and token_blacklist
        with patch("app.api.v1.deps.auth.token_blacklist") as mock_blacklist_deps:
            mock_blacklist_deps.is_revoked = AsyncMock(return_value=False)
            mock_blacklist_deps.get_user_revocation_time = AsyncMock(return_value=None)

            response = await client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {token_no_jti}"},
            )

            assert response.status_code == 401, f"Response: {response.text}"
            data = response.json()
            assert "Invalid token format" in data["detail"]

    @pytest.mark.anyio
    async def test_logout_token_without_exp(
        self,
        client: AsyncClient,
        user: User,
    ):
        """Test logout fails when token doesn't have exp claim."""
        # Create token without exp (will be invalid anyway due to jose validation)
        token_no_exp = jwt.encode(
            {
                "sub": str(user.id),
                "iat": datetime.now(UTC),
                "type": "access",
                "jti": str(uuid.uuid4()),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        # Mock get_current_user to pass authentication
        with patch("app.api.v1.endpoints.auth.get_current_user") as mock_get_user:
            mock_get_user.return_value = user

            response = await client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {token_no_exp}"},
            )

            # Should fail with invalid token format since exp is missing
            assert response.status_code == 401, f"Response: {response.text}"

    @pytest.mark.anyio
    async def test_logout_jwt_decode_error(
        self,
        client: AsyncClient,
        user: User,
    ):
        """Test logout handles JWT decode errors gracefully."""
        # Create a token with wrong secret key
        wrong_key_token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) + timedelta(hours=1),
                "iat": datetime.now(UTC),
                "type": "access",
                "jti": str(uuid.uuid4()),
            },
            "wrong-secret-key",
            algorithm=settings.jwt_algorithm,
        )

        response = await client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {wrong_key_token}"},
        )

        assert response.status_code == 401, f"Response: {response.text}"

    @pytest.mark.anyio
    async def test_logout_internal_error(
        self,
        client: AsyncClient,
        user: User,
        default_password: str,
    ):
        """Test logout handles internal errors gracefully."""
        # First login to get tokens
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": user.username,
                "password": default_password,
            },
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        access_token = token_data["access_token"]

        # Mock token_blacklist to raise an exception
        with patch("app.api.v1.endpoints.auth.token_blacklist") as mock_blacklist:
            mock_blacklist.revoke_token = AsyncMock(side_effect=Exception("Database error"))

            response = await client.post(
                "/api/v1/auth/logout",
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
            "/api/v1/auth/login",
            data={
                "username": user.username,
                "password": default_password,
            },
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        access_token = token_data["access_token"]

        # Mock token_blacklist for logout
        with patch("app.api.v1.endpoints.auth.token_blacklist") as mock_blacklist:
            mock_blacklist.revoke_token = AsyncMock(return_value=True)

            # Logout
            logout_response = await client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert logout_response.status_code == 200

        # Mock token_blacklist to return True for is_revoked (token is blacklisted)
        with patch("app.api.v1.deps.auth.token_blacklist") as mock_blacklist:
            mock_blacklist.is_revoked = AsyncMock(return_value=True)
            mock_blacklist.get_user_revocation_time = AsyncMock(return_value=None)

            # Try to use the revoked token
            response = await client.get(
                "/api/v1/users/me",
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
            "/api/v1/auth/login",
            data={
                "username": user.username,
                "password": default_password,
            },
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        access_token = token_data["access_token"]

        # Mock token_blacklist to return a revocation time in the future of token's iat
        with patch("app.api.v1.deps.auth.token_blacklist") as mock_blacklist:
            mock_blacklist.is_revoked = AsyncMock(return_value=False)
            # Set revocation time to now (after token was issued)
            mock_blacklist.get_user_revocation_time = AsyncMock(
                return_value=int(datetime.now(UTC).timestamp()) + 1
            )

            # Try to use the token
            response = await client.get(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            assert response.status_code == 401, f"Response: {response.text}"
            data = response.json()
            assert "revoked" in data["detail"].lower()
