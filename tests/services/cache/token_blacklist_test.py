from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import Environment
from app.services.cache.token_blacklist import TokenBlacklist


class TestTokenBlacklistRevokeToken:
    """Tests for revoking tokens."""

    @pytest.mark.anyio
    async def test_revoke_token_success(self, mock_redis_client: AsyncMock):
        """Test successfully revoking a token."""
        blacklist = TokenBlacklist()
        blacklist.redis_client = mock_redis_client
        mock_redis_client.setex = AsyncMock(return_value=True)

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await blacklist.revoke_token("test-jti-123", 3600)

            assert result is True
            mock_redis_client.setex.assert_called_once_with(
                "token:blacklist:test-jti-123", 3600, "revoked"
            )

    @pytest.mark.anyio
    async def test_revoke_token_local_environment(self):
        """Test revoke_token skips in LOCAL environment."""
        blacklist = TokenBlacklist()

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.LOCAL

            result = await blacklist.revoke_token("test-jti-123", 3600)

            assert result is True

    @pytest.mark.anyio
    async def test_revoke_token_no_redis_client(self):
        """Test revoke_token when Redis client is not initialized."""
        blacklist = TokenBlacklist()
        blacklist._redis_client = None

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await blacklist.revoke_token("test-jti-123", 3600)

            assert result is False

    @pytest.mark.anyio
    async def test_revoke_token_redis_exception(self, mock_redis_client: AsyncMock):
        """Test revoke_token handles Redis exceptions."""
        blacklist = TokenBlacklist()
        blacklist.redis_client = mock_redis_client
        mock_redis_client.setex = AsyncMock(side_effect=Exception("Redis connection error"))

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await blacklist.revoke_token("test-jti-123", 3600)

            assert result is False


class TestTokenBlacklistIsRevoked:
    """Tests for checking if a token is revoked."""

    @pytest.mark.anyio
    async def test_is_revoked_true(self, mock_redis_client: AsyncMock):
        """Test is_revoked returns True for revoked token."""
        blacklist = TokenBlacklist()
        blacklist.redis_client = mock_redis_client
        mock_redis_client.exists = AsyncMock(return_value=1)

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await blacklist.is_revoked("revoked-jti")

            assert result is True
            mock_redis_client.exists.assert_called_once_with("token:blacklist:revoked-jti")

    @pytest.mark.anyio
    async def test_is_revoked_false(self, mock_redis_client: AsyncMock):
        """Test is_revoked returns False for valid token."""
        blacklist = TokenBlacklist()
        blacklist.redis_client = mock_redis_client
        mock_redis_client.exists = AsyncMock(return_value=0)

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await blacklist.is_revoked("valid-jti")

            assert result is False

    @pytest.mark.anyio
    async def test_is_revoked_local_environment(self):
        """Test is_revoked returns False in LOCAL environment."""
        blacklist = TokenBlacklist()

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.LOCAL

            result = await blacklist.is_revoked("any-jti")

            assert result is False

    @pytest.mark.anyio
    async def test_is_revoked_no_redis_client(self):
        """Test is_revoked returns False (fail open) when Redis unavailable."""
        blacklist = TokenBlacklist()
        blacklist._redis_client = None

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await blacklist.is_revoked("any-jti")

            # Fail open - allows request when Redis is unavailable
            assert result is False

    @pytest.mark.anyio
    async def test_is_revoked_redis_exception(self, mock_redis_client: AsyncMock):
        """Test is_revoked handles Redis exceptions (fail open)."""
        blacklist = TokenBlacklist()
        blacklist.redis_client = mock_redis_client
        mock_redis_client.exists = AsyncMock(side_effect=Exception("Redis error"))

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await blacklist.is_revoked("any-jti")

            # Fail open on error
            assert result is False


class TestTokenBlacklistRevokeAllUserTokens:
    """Tests for revoking all tokens for a user."""

    @pytest.mark.anyio
    async def test_revoke_all_user_tokens_success(self, mock_redis_client: AsyncMock):
        """Test successfully revoking all user tokens."""
        blacklist = TokenBlacklist()
        blacklist.redis_client = mock_redis_client
        mock_redis_client.setex = AsyncMock(return_value=True)

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await blacklist.revoke_all_user_tokens("user-123", 7200)

            assert result is True
            # Verify it was called with user-specific key
            call_args = mock_redis_client.setex.call_args
            assert call_args[0][0] == "token:revoke_all:user-123"
            assert call_args[0][1] == 7200

    @pytest.mark.anyio
    async def test_revoke_all_user_tokens_local_environment(self):
        """Test revoke_all_user_tokens skips in LOCAL environment."""
        blacklist = TokenBlacklist()

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.LOCAL

            result = await blacklist.revoke_all_user_tokens("user-123", 7200)

            assert result is True

    @pytest.mark.anyio
    async def test_revoke_all_user_tokens_no_redis_client(self):
        """Test revoke_all_user_tokens when Redis unavailable."""
        blacklist = TokenBlacklist()
        blacklist._redis_client = None

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await blacklist.revoke_all_user_tokens("user-123", 7200)

            assert result is False

    @pytest.mark.anyio
    async def test_revoke_all_user_tokens_redis_exception(self, mock_redis_client: AsyncMock):
        """Test revoke_all_user_tokens handles exceptions."""
        blacklist = TokenBlacklist()
        blacklist.redis_client = mock_redis_client
        mock_redis_client.setex = AsyncMock(side_effect=Exception("Redis error"))

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await blacklist.revoke_all_user_tokens("user-123", 7200)

            assert result is False


class TestTokenBlacklistGetUserRevocationTime:
    """Tests for getting user revocation time."""

    @pytest.mark.anyio
    async def test_get_user_revocation_time_exists(self, mock_redis_client: AsyncMock):
        """Test getting revocation time when it exists."""
        blacklist = TokenBlacklist()
        blacklist.redis_client = mock_redis_client
        mock_redis_client.get = AsyncMock(return_value="1704067200")  # Some Unix timestamp

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await blacklist.get_user_revocation_time("user-123")

            assert result == 1704067200
            mock_redis_client.get.assert_called_once_with("token:revoke_all:user-123")

    @pytest.mark.anyio
    async def test_get_user_revocation_time_not_exists(self, mock_redis_client: AsyncMock):
        """Test getting revocation time when it doesn't exist."""
        blacklist = TokenBlacklist()
        blacklist.redis_client = mock_redis_client
        mock_redis_client.get = AsyncMock(return_value=None)

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await blacklist.get_user_revocation_time("user-123")

            assert result is None

    @pytest.mark.anyio
    async def test_get_user_revocation_time_local_environment(self):
        """Test get_user_revocation_time in LOCAL environment."""
        blacklist = TokenBlacklist()

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.LOCAL

            result = await blacklist.get_user_revocation_time("user-123")

            assert result is None

    @pytest.mark.anyio
    async def test_get_user_revocation_time_no_redis_client(self):
        """Test get_user_revocation_time when Redis unavailable."""
        blacklist = TokenBlacklist()
        blacklist._redis_client = None

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await blacklist.get_user_revocation_time("user-123")

            assert result is None

    @pytest.mark.anyio
    async def test_get_user_revocation_time_redis_exception(self, mock_redis_client: AsyncMock):
        """Test get_user_revocation_time handles exceptions."""
        blacklist = TokenBlacklist()
        blacklist.redis_client = mock_redis_client
        mock_redis_client.get = AsyncMock(side_effect=Exception("Redis error"))

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await blacklist.get_user_revocation_time("user-123")

            assert result is None


class TestTokenBlacklistKeyPrefix:
    """Tests for key prefix functionality."""

    def test_key_prefix_constant(self):
        """Test KEY_PREFIX is correctly defined."""
        assert TokenBlacklist.KEY_PREFIX == "token:blacklist:"

    @pytest.mark.anyio
    async def test_keys_use_correct_prefix(self, mock_redis_client: AsyncMock):
        """Test that keys use the correct prefix."""
        blacklist = TokenBlacklist()
        blacklist.redis_client = mock_redis_client
        mock_redis_client.setex = AsyncMock(return_value=True)
        mock_redis_client.exists = AsyncMock(return_value=0)

        with patch("app.services.cache.token_blacklist.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            await blacklist.revoke_token("my-jti", 3600)
            await blacklist.is_revoked("my-jti")

            # Verify correct key format
            setex_key = mock_redis_client.setex.call_args[0][0]
            exists_key = mock_redis_client.exists.call_args[0][0]

            assert setex_key == "token:blacklist:my-jti"
            assert exists_key == "token:blacklist:my-jti"


class TestTokenBlacklistGlobalInstance:
    """Tests for global token_blacklist instance."""

    def test_global_instance_exists(self):
        """Test that global token_blacklist instance exists."""
        from app.services.cache.token_blacklist import token_blacklist

        assert token_blacklist is not None
        assert isinstance(token_blacklist, TokenBlacklist)
