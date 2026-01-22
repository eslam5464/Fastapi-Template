from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from jose import jwt
from jose.exceptions import JWTClaimsError, JWTError

from app.api.v1.deps.auth import generate_refresh_token, get_current_user
from app.core.config import settings
from app.core.exceptions.http_exceptions import UnauthorizedException
from app.models.user import User
from app.schemas import TokenPayload


@pytest.mark.anyio
class TestGetCurrentUserEdgeCases:
    """Test edge cases in get_current_user dependency."""

    async def test_expired_signature_error(self, db_session, user: User):
        """Test that ExpiredSignatureError is caught and handled."""
        # Create an expired token
        expired_token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) - timedelta(seconds=10),  # Expired 10 seconds ago
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(UnauthorizedException, match="Token has expired"):
            await get_current_user(expired_token, db_session)

    async def test_jwt_claims_error(self, db_session):
        """Test that JWTClaimsError is caught and handled."""
        # Create token with invalid claims
        with patch("app.api.v1.deps.auth.jwt.decode") as mock_decode:
            mock_decode.side_effect = JWTClaimsError("Invalid claims")

            with pytest.raises(UnauthorizedException, match="Token has invalid claims"):
                await get_current_user("invalid_token", db_session)

    async def test_jwt_error(self, db_session):
        """Test that general JWTError is caught and handled."""
        invalid_token = "completely.invalid.token"

        with pytest.raises(UnauthorizedException, match="Could not validate credentials"):
            await get_current_user(invalid_token, db_session)

    async def test_missing_subject(self, db_session):
        """Test that missing 'sub' in token raises exception."""
        # Create token without 'sub' claim
        token_without_sub = jwt.encode(
            {
                "exp": datetime.now(UTC) + timedelta(seconds=settings.access_token_expire_seconds),
                "iat": datetime.now(UTC),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(UnauthorizedException, match="Could not validate credentials"):
            await get_current_user(token_without_sub, db_session)

    async def test_missing_exp(self, db_session, user: User):
        """Test that missing 'exp' in token raises exception."""
        # Create token without 'exp' claim
        token_without_exp = jwt.encode(
            {
                "sub": str(user.id),
                "iat": datetime.now(UTC),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(UnauthorizedException, match="Could not validate credentials"):
            await get_current_user(token_without_exp, db_session)

    async def test_user_not_found_in_database(self, db_session):
        """Test that exception is raised when user is not found in database."""
        non_existent_user_id = 999999999

        # Create valid token for non-existent user
        valid_token = jwt.encode(
            {
                "sub": str(non_existent_user_id),
                "exp": datetime.now(UTC) + timedelta(seconds=settings.access_token_expire_seconds),
                "iat": datetime.now(UTC),
                "type": "access",
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(UnauthorizedException, match="Could not validate credentials"):
            await get_current_user(valid_token, db_session)

    async def test_token_expired_after_decode(self, db_session, user: User):
        """Test expiration check after successful decode."""
        # Create token that just expired (edge case where exp is in payload but expired)
        token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": int((datetime.now(UTC) - timedelta(seconds=1)).timestamp()),
                "iat": int(datetime.now(UTC).timestamp()),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        # This should be caught by either ExpiredSignatureError or the manual exp check
        with pytest.raises(UnauthorizedException):
            await get_current_user(token, db_session)

    async def test_wrong_secret_key(self, db_session, user: User):
        """Test that token signed with wrong key fails validation."""
        # Create token with different secret key
        wrong_key_token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) + timedelta(seconds=3600),
            },
            "wrong_secret_key_12345",
            algorithm=settings.jwt_algorithm,
        )

        with pytest.raises(UnauthorizedException):
            await get_current_user(wrong_key_token, db_session)


@pytest.mark.anyio
class TestGenerateRefreshToken:
    """Test generate_refresh_token function."""

    async def test_success(self, db_session, user: User):
        """Test successful refresh token generation."""
        # Create valid refresh token
        refresh_token = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) + timedelta(days=7),
                "type": "refresh",
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        token_payload = TokenPayload(refresh_token=refresh_token)

        result = await generate_refresh_token(token_payload, db_session)

        assert "access_token" in result
        assert "refresh_token" in result
        assert isinstance(result["access_token"], str)
        assert isinstance(result["refresh_token"], str)

    async def test_invalid_token_format(self, db_session):
        """Test that invalid token format raises UnauthorizedException."""
        token_payload = TokenPayload(refresh_token="invalid.token.format")

        with pytest.raises(UnauthorizedException, match="Invalid refresh token"):
            await generate_refresh_token(token_payload, db_session)

    async def test_missing_user_id_in_token(self, db_session):
        """Test that token without user_id raises exception."""
        # Create token without 'sub'
        refresh_token = jwt.encode(
            {
                "exp": datetime.now(UTC) + timedelta(days=7),
                "iat": datetime.now(UTC),
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        token_payload = TokenPayload(refresh_token=refresh_token)

        with pytest.raises(UnauthorizedException, match="Invalid refresh token"):
            await generate_refresh_token(token_payload, db_session)

    async def test_user_not_found_in_database(self, db_session):
        """Test that non-existent user raises exception."""
        non_existent_user_id = 999999999

        # Create valid token for non-existent user
        refresh_token = jwt.encode(
            {
                "sub": str(non_existent_user_id),
                "exp": datetime.now(UTC) + timedelta(days=7),
                "type": "refresh",
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        token_payload = TokenPayload(refresh_token=refresh_token)

        with pytest.raises(UnauthorizedException, match="Invalid user"):
            await generate_refresh_token(token_payload, db_session)

    async def test_jwt_decode_error(self, db_session):
        """Test that JWT decode errors are handled."""
        with patch("app.api.v1.deps.auth.jwt.decode") as mock_decode:
            mock_decode.side_effect = JWTError("Decode failed")

            token_payload = TokenPayload(refresh_token="some_token")

            with pytest.raises(UnauthorizedException, match="Invalid refresh token"):
                await generate_refresh_token(token_payload, db_session)

    async def test_wrong_secret_key_for_refresh(self, db_session):
        """Test that refresh token with wrong secret key fails."""
        # Create token with wrong key
        refresh_token = jwt.encode(
            {
                "sub": str(999999999),
                "exp": datetime.now(UTC) + timedelta(days=7),
            },
            "wrong_secret_key",
            algorithm=settings.jwt_algorithm,
        )

        token_payload = TokenPayload(refresh_token=refresh_token)

        with pytest.raises(UnauthorizedException, match="Invalid refresh token"):
            await generate_refresh_token(token_payload, db_session)

    async def test_returns_new_tokens(self, db_session, user: User):
        """Test that new access and refresh tokens are different from input."""
        # Create valid refresh token
        original_refresh = jwt.encode(
            {
                "sub": str(user.id),
                "exp": datetime.now(UTC) + timedelta(days=7),
                "type": "refresh",
            },
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )

        token_payload = TokenPayload(refresh_token=original_refresh)

        result = await generate_refresh_token(token_payload, db_session)

        # New tokens should be different from original
        assert result["access_token"] != original_refresh
        assert result["refresh_token"] != original_refresh
        assert result["access_token"] != result["refresh_token"]
