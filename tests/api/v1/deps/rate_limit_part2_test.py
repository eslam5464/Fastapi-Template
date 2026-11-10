from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request

from app.api.v1.deps.rate_limit import (
    create_rate_limit,
    create_rate_limit_ip_only,
)
from app.core.exceptions.http_exceptions import TooManyRequestsException


@pytest.mark.anyio
class TestCreateRateLimitIPOnly:
    """Test create_rate_limit_ip_only factory function."""

    async def test_creates_limiter_with_custom_limit(self):
        """Test that factory creates limiter with custom limit."""
        custom_limit = 5
        custom_window = 300
        custom_prefix = "export"

        rate_limiter = create_rate_limit_ip_only(limit=custom_limit, window=custom_window, prefix=custom_prefix)

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
class TestCreateRateLimit:
    """Test create_rate_limit wrapper function."""

    async def test_default_is_ip_based(self):
        """Test that the default limiter counts per IP address."""
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
        rate_limiter = create_rate_limit(limit=2, window=30, prefix="strict")

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
