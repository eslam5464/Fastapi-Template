"""Tests for the logout endpoint."""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from jose import jwt

from app.core.config import settings
from app.models import User


class TestLogoutEndpoint:
    """Test suite for POST /v1/auth/logout endpoint."""

    @pytest.mark.anyio
    async def test_logout_success(
        self,
        client: AsyncClient,
        user: User,
        default_password: str,
    ):
        """Test successful logout with valid access token."""
        login_response = await client.post(
            "/v1/auth/login",
            data={
                "username": user.username,
                "password": default_password,
            },
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        response = await client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Successfully logged out"
        # True only when the project revokes tokens (logout_revocation_test.py).
        assert isinstance(data["revoked"], bool)

    @pytest.mark.anyio
    async def test_logout_invalid_token(
        self,
        client: AsyncClient,
    ):
        """Test logout fails with invalid token."""
        response = await client.post(
            "/v1/auth/logout",
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
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401

    @pytest.mark.anyio
    async def test_logout_no_token(
        self,
        client: AsyncClient,
    ):
        """Test logout fails without authorization header."""
        response = await client.post("/v1/auth/logout")

        assert response.status_code == 401

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
                "/v1/auth/logout",
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
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {wrong_key_token}"},
        )

        assert response.status_code == 401, f"Response: {response.text}"
