from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request

from app.api.v1.deps.rate_limit import (
    create_rate_limit,
    create_rate_limit_ip_only,
    create_rate_limit_user_and_ip,
    create_rate_limit_user_only,
)
from app.core.exceptions.http_exceptions import TooManyRequestsException
from app.models.user import User


@pytest.mark.anyio
class TestCreateRateLimitIPOnly:
    """Test create_rate_limit_ip_only factory function."""

    async def test_creates_limiter_with_custom_limit(self):
        """Test that factory creates limiter with custom limit."""
        custom_limit = 5
        custom_window = 300
        custom_prefix = "export"

        rate_limiter = create_rate_limit_ip_only(
            limit=custom_limit, window=custom_window, prefix=custom_prefix
        )

        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {"limit": custom_limit, "remaining": 4, "reset_time": 300, "current": 1}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="192.168.1.1"):
                mock_check.return_value = (True, mock_info)

                await rate_limiter(request)

                # Verify correct parameters
                mock_check.assert_called_once_with(
                    key=f"ratelimit:{custom_prefix}:192.168.1.1",
                    limit=custom_limit,
                    window=custom_window,
                )

    async def test_enforces_limit(self):
        """Test that created limiter enforces the limit."""
        rate_limiter = create_rate_limit_ip_only(limit=3, window=60, prefix="test")

        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {"limit": 3, "remaining": 0, "reset_time": 60, "current": 3}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="192.168.1.1"):
                mock_check.return_value = (False, mock_info)

                with pytest.raises(TooManyRequestsException) as exc_info:
                    await rate_limiter(request)

                exception = exc_info.value
                assert exception.headers is not None
                assert exception.headers["X-RateLimit-Limit"] == "3"
                assert exception.headers["X-RateLimit-Remaining"] == "0"

    async def test_uses_ip_address(self):
        """Test that limiter uses IP address for rate limiting."""
        rate_limiter = create_rate_limit_ip_only(limit=10, window=60, prefix="custom")

        request = MagicMock(spec=Request)
        request.client = MagicMock(host="203.0.113.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {"limit": 10, "remaining": 9, "reset_time": 60, "current": 1}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="203.0.113.1"):
                mock_check.return_value = (True, mock_info)

                await rate_limiter(request)

                call_args = mock_check.call_args[1]
                assert "203.0.113.1" in call_args["key"]
                assert call_args["key"] == "ratelimit:custom:203.0.113.1"


@pytest.mark.anyio
class TestCreateRateLimitUserOnly:
    """Test create_rate_limit_user_only factory function."""

    async def test_creates_limiter_with_custom_limit(self, user: User):
        """Test that factory creates user-based limiter with custom limit."""
        custom_limit = 20
        custom_window = 600
        custom_prefix = "upload"

        rate_limiter = create_rate_limit_user_only(
            limit=custom_limit, window=custom_window, prefix=custom_prefix
        )

        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {"limit": custom_limit, "remaining": 19, "reset_time": 600, "current": 1}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            mock_check.return_value = (True, mock_info)

            await rate_limiter(request, user)

            # Verify correct parameters
            mock_check.assert_called_once_with(
                key=f"ratelimit:user:{custom_prefix}:{user.id}",
                limit=custom_limit,
                window=custom_window,
            )

    async def test_enforces_limit(self, user: User):
        """Test that created user limiter enforces the limit."""
        rate_limiter = create_rate_limit_user_only(limit=5, window=60, prefix="test")

        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {"limit": 5, "remaining": 0, "reset_time": 60, "current": 5}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            mock_check.return_value = (False, mock_info)

            with pytest.raises(TooManyRequestsException) as exc_info:
                await rate_limiter(request, user)

            exception = exc_info.value
            assert exception.headers is not None
            assert exception.headers["X-RateLimit-Limit"] == "5"

    async def test_uses_user_id(self, user: User):
        """Test that limiter uses user ID for rate limiting."""
        rate_limiter = create_rate_limit_user_only(limit=10, window=60, prefix="custom")

        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {"limit": 10, "remaining": 9, "reset_time": 60, "current": 1}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            mock_check.return_value = (True, mock_info)

            await rate_limiter(request, user)

            call_args = mock_check.call_args[1]
            assert str(user.id) in call_args["key"]
            assert call_args["key"] == f"ratelimit:user:custom:{user.id}"


@pytest.mark.anyio
class TestCreateRateLimitUserAndIP:
    """Test create_rate_limit_user_and_ip factory function."""

    async def test_creates_limiter_with_custom_limit(self, user: User):
        """Test that factory creates combined user+IP limiter."""
        custom_limit = 15
        custom_window = 600
        custom_prefix = "sensitive"

        rate_limiter = create_rate_limit_user_and_ip(
            limit=custom_limit, window=custom_window, prefix=custom_prefix
        )

        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {"limit": custom_limit, "remaining": 14, "reset_time": 600, "current": 1}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="192.168.1.1"):
                mock_check.return_value = (True, mock_info)

                await rate_limiter(request, user)

                # Verify correct parameters with both user ID and IP
                mock_check.assert_called_once_with(
                    key=f"ratelimit:userip:{custom_prefix}:{user.id}:192.168.1.1",
                    limit=custom_limit,
                    window=custom_window,
                )

    async def test_enforces_limit(self, user: User):
        """Test that created combined limiter enforces the limit."""
        rate_limiter = create_rate_limit_user_and_ip(limit=7, window=60, prefix="test")

        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {"limit": 7, "remaining": 0, "reset_time": 60, "current": 7}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="192.168.1.1"):
                mock_check.return_value = (False, mock_info)

                with pytest.raises(TooManyRequestsException) as exc_info:
                    await rate_limiter(request, user)

                exception = exc_info.value
                assert exception.headers is not None
                assert exception.headers["X-RateLimit-Limit"] == "7"

    async def test_uses_both_user_id_and_ip(self, user: User):
        """Test that limiter uses both user ID and IP address."""
        rate_limiter = create_rate_limit_user_and_ip(limit=10, window=60, prefix="combined")

        request = MagicMock(spec=Request)
        request.client = MagicMock(host="203.0.113.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {"limit": 10, "remaining": 9, "reset_time": 60, "current": 1}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="203.0.113.1"):
                mock_check.return_value = (True, mock_info)

                await rate_limiter(request, user)

                call_args = mock_check.call_args[1]
                # Key should contain both user ID and IP
                assert str(user.id) in call_args["key"]
                assert "203.0.113.1" in call_args["key"]
                assert call_args["key"] == f"ratelimit:userip:combined:{user.id}:203.0.113.1"

    async def test_different_ips_separate_limits(self, user: User):
        """Test that same user from different IPs has separate limits."""
        rate_limiter = create_rate_limit_user_and_ip(limit=10, window=60, prefix="test")

        request = MagicMock(spec=Request)
        request.headers = {}
        request.state = MagicMock()

        mock_info = {"limit": 10, "remaining": 9, "reset_time": 60, "current": 1}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            mock_check.return_value = (True, mock_info)

            # First IP
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="192.168.1.1"):
                request.client = MagicMock(host="192.168.1.1")
                await rate_limiter(request, user)
                first_key = mock_check.call_args[1]["key"]

            # Second IP
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="192.168.1.2"):
                request.client = MagicMock(host="192.168.1.2")
                await rate_limiter(request, user)
                second_key = mock_check.call_args[1]["key"]

            # Keys should be different
            assert first_key != second_key
            assert "192.168.1.1" in first_key
            assert "192.168.1.2" in second_key


@pytest.mark.anyio
class TestCreateRateLimit:
    """Test create_rate_limit wrapper function."""

    async def test_user_based_true_creates_user_limiter(self, user: User):
        """Test that user_based=True creates user-only limiter."""
        rate_limiter = create_rate_limit(limit=25, window=300, prefix="test", user_based=True)

        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {"limit": 25, "remaining": 24, "reset_time": 300, "current": 1}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            mock_check.return_value = (True, mock_info)

            await rate_limiter(request, user)

            # Should use user-based key
            call_args = mock_check.call_args[1]
            assert call_args["key"] == f"ratelimit:user:test:{user.id}"
            assert call_args["limit"] == 25
            assert call_args["window"] == 300

    async def test_user_based_false_creates_ip_limiter(self):
        """Test that user_based=False creates IP-only limiter."""
        rate_limiter = create_rate_limit(limit=30, window=120, prefix="iptest", user_based=False)

        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {"limit": 30, "remaining": 29, "reset_time": 120, "current": 1}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="192.168.1.1"):
                mock_check.return_value = (True, mock_info)

                await rate_limiter(request)

                # Should use IP-based key
                call_args = mock_check.call_args[1]
                assert call_args["key"] == "ratelimit:iptest:192.168.1.1"
                assert call_args["limit"] == 30
                assert call_args["window"] == 120

    async def test_default_user_based_is_false(self):
        """Test that default behavior is user_based=False."""
        rate_limiter = create_rate_limit(limit=10, window=60, prefix="default")

        request = MagicMock(spec=Request)
        request.client = MagicMock(host="10.0.0.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {"limit": 10, "remaining": 9, "reset_time": 60, "current": 1}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="10.0.0.1"):
                mock_check.return_value = (True, mock_info)

                # Should work without user parameter (IP-based)
                await rate_limiter(request)

                call_args = mock_check.call_args[1]
                assert "10.0.0.1" in call_args["key"]

    async def test_enforces_custom_limits(self):
        """Test that custom limits are enforced correctly."""
        rate_limiter = create_rate_limit(limit=2, window=30, prefix="strict", user_based=False)

        request = MagicMock(spec=Request)
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}
        request.state = MagicMock()

        mock_info = {"limit": 2, "remaining": 0, "reset_time": 30, "current": 2}

        with patch("app.api.v1.deps.rate_limit.rate_limiter.check_rate_limit") as mock_check:
            with patch("app.api.v1.deps.rate_limit.get_client_ip", return_value="192.168.1.1"):
                mock_check.return_value = (False, mock_info)

                with pytest.raises(TooManyRequestsException) as exc_info:
                    await rate_limiter(request)

                exception = exc_info.value
                assert exception.headers is not None
                assert exception.headers["X-RateLimit-Limit"] == "2"
                assert exception.headers["X-RateLimit-Reset"] == "30"
