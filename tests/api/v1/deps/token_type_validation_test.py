import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_auth_service, get_current_user
from app.core.config import settings
from app.core.exceptions.http_exceptions import UnauthorizedException
from app.models import User


class TestAccessTokenTypeValidation:
    """Tests for access token type validation in get_current_user."""

    @pytest.mark.anyio
    async def test_access_token_wrong_type_refresh(
        self,
        db_session: AsyncSession,
        user: User,
    ):
        """Test get_current_user rejects refresh token used as access token."""
        # Create a refresh token (wrong type for get_current_user)
        refresh_token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) + timedelta(hours=24),
                "iat": datetime.now(UTC),
                "type": "refresh",  # Wrong type - should be "access"
                "jti": str(uuid.uuid4()),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(UnauthorizedException) as exc_info:
            await get_current_user(token=refresh_token, service=get_auth_service(db_session))

        assert exc_info.value.status_code == 401
        assert "invalid claims" in str(exc_info.value.detail).lower()

    @pytest.mark.anyio
    async def test_access_token_missing_type(
        self,
        db_session: AsyncSession,
        user: User,
    ):
        """Test get_current_user rejects token without type claim."""
        # Create token without type
        token_no_type = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) + timedelta(hours=1),
                "iat": datetime.now(UTC),
                "jti": str(uuid.uuid4()),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(UnauthorizedException) as exc_info:
            await get_current_user(token=token_no_type, service=get_auth_service(db_session))

        assert exc_info.value.status_code == 401
        assert "invalid claims" in str(exc_info.value.detail).lower()

    @pytest.mark.anyio
    async def test_access_token_invalid_type_value(
        self,
        db_session: AsyncSession,
        user: User,
    ):
        """Test get_current_user rejects token with invalid type value."""
        # Create token with invalid type
        token_invalid_type = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) + timedelta(hours=1),
                "iat": datetime.now(UTC),
                "type": "invalid_type",  # Invalid type value
                "jti": str(uuid.uuid4()),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(UnauthorizedException) as exc_info:
            await get_current_user(token=token_invalid_type, service=get_auth_service(db_session))

        assert exc_info.value.status_code == 401
        assert "invalid claims" in str(exc_info.value.detail).lower()


class TestRefreshTokenTypeValidation:
    """Tests for refresh token type validation in generate_refresh_token."""

    @pytest.mark.anyio
    async def test_refresh_token_wrong_type_access(
        self,
        client: AsyncClient,
        user: User,
    ):
        """Test refresh endpoint rejects access token used as refresh token."""
        # Create an access token (wrong type for refresh endpoint)
        access_token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) + timedelta(hours=1),
                "iat": datetime.now(UTC),
                "type": "access",  # Wrong type - should be "refresh"
                "jti": str(uuid.uuid4()),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        response = await client.post(
            "/v1/auth/refresh-token",
            json={"refresh_token": access_token},
        )

        assert response.status_code == 401
        data = response.json()
        assert "invalid token type" in data["detail"].lower()

    @pytest.mark.anyio
    async def test_refresh_token_missing_type(
        self,
        client: AsyncClient,
        user: User,
    ):
        """Test refresh endpoint rejects token without type claim."""
        # Create token without type
        token_no_type = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) + timedelta(hours=24),
                "iat": datetime.now(UTC),
                "jti": str(uuid.uuid4()),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        response = await client.post(
            "/v1/auth/refresh-token",
            json={"refresh_token": token_no_type},
        )

        assert response.status_code == 401
        data = response.json()
        assert "invalid token type" in data["detail"].lower()
