from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request

from app.core.config import Environment, settings
from app.core.utils import get_client_ip


@pytest.mark.anyio
class TestGetClientIP:
    """Test get_client_ip function."""

    def test_local_environment_returns_localhost(self):
        """Test that local environment always returns localhost."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = MagicMock(host="192.168.1.1")

        with patch.object(settings, "current_environment", Environment.LOCAL):
            result = get_client_ip(request)

        assert result == "localhost"

    def test_x_forwarded_for_header(self):
        """Test X-Forwarded-For header extraction."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "203.0.113.195"}
        request.client = MagicMock(host="192.168.1.1")

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "203.0.113.195"

    def test_x_forwarded_for_multiple_ips(self):
        """Test X-Forwarded-For header with multiple IPs (takes first one)."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "203.0.113.195, 70.41.3.18, 150.172.238.178"}
        request.client = MagicMock(host="192.168.1.1")

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "203.0.113.195"

    def test_x_forwarded_for_with_spaces(self):
        """Test X-Forwarded-For header strips whitespace."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "  203.0.113.195  "}
        request.client = MagicMock(host="192.168.1.1")

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "203.0.113.195"

    def test_x_real_ip_header(self):
        """Test X-Real-IP header extraction."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Real-IP": "198.51.100.42"}
        request.client = MagicMock(host="192.168.1.1")

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "198.51.100.42"

    def test_x_real_ip_with_whitespace(self):
        """Test X-Real-IP header strips whitespace."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Real-IP": "  198.51.100.42  "}
        request.client = MagicMock(host="192.168.1.1")

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "198.51.100.42"

    def test_x_client_ip_header(self):
        """Test X-Client-IP header extraction."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Client-IP": "192.0.2.1"}
        request.client = MagicMock(host="192.168.1.1")

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "192.0.2.1"

    def test_x_client_ip_with_whitespace(self):
        """Test X-Client-IP header strips whitespace."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Client-IP": "  192.0.2.1  "}
        request.client = MagicMock(host="192.168.1.1")

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "192.0.2.1"

    def test_request_client_host_fallback(self):
        """Test fallback to request.client.host when no headers present."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = MagicMock(host="192.168.1.100")

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "192.168.1.100"

    def test_unknown_when_no_client(self):
        """Test returns 'unknown' when request.client is None."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = None

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "unknown"

    def test_header_priority_x_forwarded_for_first(self):
        """Test that X-Forwarded-For has highest priority."""
        request = MagicMock(spec=Request)
        request.headers = {
            "X-Forwarded-For": "203.0.113.195",
            "X-Real-IP": "198.51.100.42",
            "X-Client-IP": "192.0.2.1",
        }
        request.client = MagicMock(host="192.168.1.1")

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "203.0.113.195"
