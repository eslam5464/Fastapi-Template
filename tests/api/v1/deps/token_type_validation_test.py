import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps.auth import get_current_user
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

        with patch("app.api.v1.deps.auth.token_blacklist") as mock_blacklist:
            mock_blacklist.is_revoked = AsyncMock(return_value=False)
            mock_blacklist.get_user_revocation_time = AsyncMock(return_value=None)

            with pytest.raises(UnauthorizedException) as exc_info:
                await get_current_user(token=refresh_token, db=db_session)

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

        with patch("app.api.v1.deps.auth.token_blacklist") as mock_blacklist:
            mock_blacklist.is_revoked = AsyncMock(return_value=False)
            mock_blacklist.get_user_revocation_time = AsyncMock(return_value=None)

            with pytest.raises(UnauthorizedException) as exc_info:
                await get_current_user(token=token_no_type, db=db_session)

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

        with patch("app.api.v1.deps.auth.token_blacklist") as mock_blacklist:
            mock_blacklist.is_revoked = AsyncMock(return_value=False)
            mock_blacklist.get_user_revocation_time = AsyncMock(return_value=None)

            with pytest.raises(UnauthorizedException) as exc_info:
                await get_current_user(token=token_invalid_type, db=db_session)

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

        with patch("app.api.v1.deps.auth.token_blacklist") as mock_blacklist:
            mock_blacklist.is_revoked = AsyncMock(return_value=False)

            response = await client.post(
                "/api/v1/auth/refresh-token",
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

        with patch("app.api.v1.deps.auth.token_blacklist") as mock_blacklist:
            mock_blacklist.is_revoked = AsyncMock(return_value=False)

            response = await client.post(
                "/api/v1/auth/refresh-token",
                json={"refresh_token": token_no_type},
            )

            assert response.status_code == 401
            data = response.json()
            assert "invalid token type" in data["detail"].lower()

    @pytest.mark.anyio
    async def test_refresh_token_blacklisted(
        self,
        client: AsyncClient,
        user: User,
    ):
        """Test refresh endpoint rejects blacklisted refresh token."""
        # Create a valid refresh token
        refresh_token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) + timedelta(hours=24),
                "iat": datetime.now(UTC),
                "type": "refresh",
                "jti": str(uuid.uuid4()),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        # Mock token_blacklist to return True (token is blacklisted)
        with patch("app.api.v1.deps.auth.token_blacklist") as mock_blacklist:
            mock_blacklist.is_revoked = AsyncMock(return_value=True)

            response = await client.post(
                "/api/v1/auth/refresh-token",
                json={"refresh_token": refresh_token},
            )

            assert response.status_code == 401
            data = response.json()
            assert "revoked" in data["detail"].lower()


class TestTokenBlacklistIntegration:
    """Tests for token blacklist checks in authentication flow."""

    @pytest.mark.anyio
    async def test_access_token_blacklisted_jti(
        self,
        db_session: AsyncSession,
        user: User,
    ):
        """Test get_current_user rejects blacklisted access token."""
        jti = str(uuid.uuid4())

        # Create a valid access token with jti
        access_token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) + timedelta(hours=1),
                "iat": datetime.now(UTC),
                "type": "access",
                "jti": jti,
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        # Mock token_blacklist to return True for is_revoked
        with patch("app.api.v1.deps.auth.token_blacklist") as mock_blacklist:
            mock_blacklist.is_revoked = AsyncMock(return_value=True)
            mock_blacklist.get_user_revocation_time = AsyncMock(return_value=None)

            with pytest.raises(UnauthorizedException) as exc_info:
                await get_current_user(token=access_token, db=db_session)

            assert exc_info.value.status_code == 401
            assert "revoked" in str(exc_info.value.detail).lower()

            # Verify is_revoked was called with correct jti
            mock_blacklist.is_revoked.assert_called_once_with(jti)

    @pytest.mark.anyio
    async def test_token_issued_before_user_revocation(
        self,
        db_session: AsyncSession,
        user: User,
    ):
        """Test tokens issued before user revocation time are rejected."""
        issued_at = int((datetime.now(UTC) - timedelta(hours=1)).timestamp())
        revocation_time = int(datetime.now(UTC).timestamp())

        # Create a token with old iat
        access_token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) + timedelta(hours=1),
                "iat": issued_at,
                "type": "access",
                "jti": str(uuid.uuid4()),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        # Mock token_blacklist
        with patch("app.api.v1.deps.auth.token_blacklist") as mock_blacklist:
            mock_blacklist.is_revoked = AsyncMock(return_value=False)
            # Return a revocation time that's after token's iat
            mock_blacklist.get_user_revocation_time = AsyncMock(return_value=revocation_time)

            with pytest.raises(UnauthorizedException) as exc_info:
                await get_current_user(token=access_token, db=db_session)

            assert exc_info.value.status_code == 401
            assert "revoked" in str(exc_info.value.detail).lower()

    @pytest.mark.anyio
    async def test_token_issued_after_user_revocation(
        self,
        db_session: AsyncSession,
        user: User,
    ):
        """Test tokens issued after user revocation time are accepted."""
        revocation_time = int((datetime.now(UTC) - timedelta(hours=1)).timestamp())
        issued_at = int(datetime.now(UTC).timestamp())

        # Create a token with iat after revocation
        access_token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) + timedelta(hours=1),
                "iat": issued_at,
                "type": "access",
                "jti": str(uuid.uuid4()),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        # Mock token_blacklist
        with patch("app.api.v1.deps.auth.token_blacklist") as mock_blacklist:
            mock_blacklist.is_revoked = AsyncMock(return_value=False)
            # Return a revocation time that's before token's iat
            mock_blacklist.get_user_revocation_time = AsyncMock(return_value=revocation_time)

            # Should succeed
            current_user = await get_current_user(token=access_token, db=db_session)
            assert current_user.id == user.id
