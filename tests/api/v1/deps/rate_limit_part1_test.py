from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request

from app.api.v1.deps.rate_limit import (
    rate_limit_api,
    rate_limit_auth,
    rate_limit_public,
    rate_limit_user,
)
from app.core.config import settings
from app.core.exceptions.http_exceptions import TooManyRequestsException
from app.models.user import User


@pytest.mark.anyio
class TestRateLimitAuth:
    """Test rate_limit_auth dependency for authentication endpoints."""

    async def test_allows_request_under_limit(self):
        """Test that requests under limit are allowed."""
        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        # Mock rate limiter to allow request
        mock_info = {
            "limit": 10,
            "remaining": 9,
            "reset_time": 60,
            "current": 1,
        }

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="192.168.1.1"):
                mock_check.return_value = (True, mock_info)

                # Should not raise exception
                await rate_limit_auth(request)

                # Verify rate limit info stored in request state
                assert request.state.rate_limit_info == mock_info

                # Verify check_rate_limit called with correct params
                mock_check.assert_called_once_with(
                    key="ratelimit:auth:192.168.1.1",
                    limit=settings.rate_limit_strict,
                    window=settings.rate_limit_window,
                )

    async def test_blocks_request_over_limit(self):
        """Test that requests over limit are blocked with TooManyRequestsException."""
        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        # Mock rate limiter to deny request
        mock_info = {
            "limit": 10,
            "remaining": 0,
            "reset_time": 60,
            "current": 10,
        }

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="192.168.1.1"):
                mock_check.return_value = (False, mock_info)

                # Should raise TooManyRequestsException
                with pytest.raises(TooManyRequestsException) as exc_info:
                    await rate_limit_auth(request)

                # Verify exception details
                exception = exc_info.value
                assert "Rate limit exceeded" in exception.detail
                assert exception.headers is not None
                assert exception.headers["X-RateLimit-Limit"] == "10"
                assert exception.headers["X-RateLimit-Remaining"] == "0"
                assert exception.headers["X-RateLimit-Reset"] == "60"

                # Verify info stored even when blocked
                assert request.state.rate_limit_info == mock_info

    async def test_stores_info_in_request_state(self):
        """Test that rate limit info is always stored in request state."""
        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {
            "limit": 10,
            "remaining": 5,
            "reset_time": 45,
            "current": 5,
        }

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="192.168.1.1"):
                mock_check.return_value = (True, mock_info)

                await rate_limit_auth(request)

                # Verify info is stored
                assert hasattr(request.state, "rate_limit_info")
                assert request.state.rate_limit_info == mock_info

    async def test_uses_correct_key_prefix(self):
        """Test that correct rate limit key prefix is used."""
        request = MagicMock(spec=Request)
        request.client = MagicMock(host="203.0.113.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {"limit": 10, "remaining": 9, "reset_time": 60, "current": 1}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="203.0.113.1"):
                mock_check.return_value = (True, mock_info)

                await rate_limit_auth(request)

                # Verify key starts with auth prefix
                call_args = mock_check.call_args[1]
                assert call_args["key"] == "ratelimit:auth:203.0.113.1"


@pytest.mark.anyio
class TestRateLimitAPI:
    """Test rate_limit_api dependency for general API endpoints."""

    async def test_allows_request_under_limit(self):
        """Test that requests under limit are allowed."""
        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {
            "limit": 100,
            "remaining": 99,
            "reset_time": 60,
            "current": 1,
        }

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="192.168.1.1"):
                mock_check.return_value = (True, mock_info)

                await rate_limit_api(request)

                assert request.state.rate_limit_info == mock_info
                mock_check.assert_called_once_with(
                    key="ratelimit:api:192.168.1.1",
                    limit=settings.rate_limit_default,
                    window=settings.rate_limit_window,
                )

    async def test_blocks_request_over_limit(self):
        """Test that requests over limit are blocked."""
        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {
            "limit": 100,
            "remaining": 0,
            "reset_time": 60,
            "current": 100,
        }

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="192.168.1.1"):
                mock_check.return_value = (False, mock_info)

                with pytest.raises(TooManyRequestsException) as exc_info:
                    await rate_limit_api(request)

                exception = exc_info.value
                assert exception.headers is not None
                assert exception.headers["X-RateLimit-Limit"] == "100"

    async def test_uses_correct_key_prefix(self):
        """Test that correct rate limit key prefix is used."""
        request = MagicMock(spec=Request)
        request.client = MagicMock(host="10.0.0.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {"limit": 100, "remaining": 99, "reset_time": 60, "current": 1}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="10.0.0.1"):
                mock_check.return_value = (True, mock_info)

                await rate_limit_api(request)

                call_args = mock_check.call_args[1]
                assert call_args["key"] == "ratelimit:api:10.0.0.1"


@pytest.mark.anyio
class TestRateLimitPublic:
    """Test rate_limit_public dependency for public endpoints."""

    async def test_allows_request_under_limit(self):
        """Test that requests under limit are allowed."""
        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {
            "limit": 1000,
            "remaining": 999,
            "reset_time": 60,
            "current": 1,
        }

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="192.168.1.1"):
                mock_check.return_value = (True, mock_info)

                await rate_limit_public(request)

                assert request.state.rate_limit_info == mock_info
                mock_check.assert_called_once_with(
                    key="ratelimit:public:192.168.1.1",
                    limit=settings.rate_limit_lenient,
                    window=settings.rate_limit_window,
                )

    async def test_blocks_request_over_limit(self):
        """Test that requests over limit are blocked."""
        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {
            "limit": 1000,
            "remaining": 0,
            "reset_time": 60,
            "current": 1000,
        }

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="192.168.1.1"):
                mock_check.return_value = (False, mock_info)

                with pytest.raises(TooManyRequestsException) as exc_info:
                    await rate_limit_public(request)

                exception = exc_info.value
                assert exception.headers is not None
                assert exception.headers["X-RateLimit-Limit"] == "1000"

    async def test_uses_correct_key_prefix(self):
        """Test that correct rate limit key prefix is used."""
        request = MagicMock(spec=Request)
        request.client = MagicMock(host="172.16.0.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {"limit": 1000, "remaining": 999, "reset_time": 60, "current": 1}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="172.16.0.1"):
                mock_check.return_value = (True, mock_info)

                await rate_limit_public(request)

                call_args = mock_check.call_args[1]
                assert call_args["key"] == "ratelimit:public:172.16.0.1"


@pytest.mark.anyio
class TestRateLimitUser:
    """Test rate_limit_user dependency for authenticated user endpoints."""

    async def test_allows_request_under_limit(self, user: User):
        """Test that requests under limit are allowed."""
        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {
            "limit": 300,
            "remaining": 299,
            "reset_time": 60,
            "current": 1,
        }

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            mock_check.return_value = (True, mock_info)

            await rate_limit_user(request, user)

            assert request.state.rate_limit_info == mock_info
            mock_check.assert_called_once_with(
                key=f"ratelimit:user:{user.id}",
                limit=settings.rate_limit_user,
                window=settings.rate_limit_window,
            )

    async def test_blocks_request_over_limit(self, user: User):
        """Test that requests over limit are blocked."""
        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {
            "limit": 300,
            "remaining": 0,
            "reset_time": 60,
            "current": 300,
        }

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            mock_check.return_value = (False, mock_info)

            with pytest.raises(TooManyRequestsException) as exc_info:
                await rate_limit_user(request, user)

            exception = exc_info.value
            assert exception.headers is not None
            assert exception.headers["X-RateLimit-Limit"] == "300"

    async def test_uses_user_id_not_ip(self, user: User, other_user: User):
        """Test that rate limiting is based on user ID, not IP address."""
        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")  # Same IP for both users
        request.headers = {}
        request.state = MagicMock()

        mock_info = {"limit": 300, "remaining": 299, "reset_time": 60, "current": 1}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            mock_check.return_value = (True, mock_info)

            # First user
            await rate_limit_user(request, user)
            first_call_key = mock_check.call_args[1]["key"]

            # Second user with same IP
            await rate_limit_user(request, other_user)
            second_call_key = mock_check.call_args[1]["key"]

            # Keys should be different (based on user ID)
            assert first_call_key == f"ratelimit:user:{user.id}"
            assert second_call_key == f"ratelimit:user:{other_user.id}"
            assert first_call_key != second_call_key

    async def test_custom_limit_and_window(self, user: User):
        """Test that custom limit and window parameters work."""
        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        custom_limit = 50
        custom_window = 120
        mock_info = {"limit": custom_limit, "remaining": 49, "reset_time": 120, "current": 1}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            mock_check.return_value = (True, mock_info)

            await rate_limit_user(request, user, limit=custom_limit, window=custom_window)

            mock_check.assert_called_once_with(
                key=f"ratelimit:user:{user.id}",
                limit=custom_limit,
                window=custom_window,
            )
