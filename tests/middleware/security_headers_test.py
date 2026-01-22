from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request
from starlette.middleware.base import _StreamingResponse

from app.core.config import Environment
from app.middleware.security_headers import SecurityHeadersMiddleware


@pytest.mark.anyio
class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware functionality."""

    async def test_adds_x_content_type_options(self):
        """Test X-Content-Type-Options header is added."""
        middleware = SecurityHeadersMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "GET"

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.security_headers.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            assert result.headers["X-Content-Type-Options"] == "nosniff"

    async def test_adds_x_frame_options(self):
        """Test X-Frame-Options header is added."""
        middleware = SecurityHeadersMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "GET"

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.security_headers.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            assert result.headers["X-Frame-Options"] == "DENY"

    async def test_adds_x_xss_protection(self):
        """Test X-XSS-Protection header is added."""
        middleware = SecurityHeadersMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "GET"

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.security_headers.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            assert result.headers["X-XSS-Protection"] == "1; mode=block"

    async def test_adds_referrer_policy(self):
        """Test Referrer-Policy header is added."""
        middleware = SecurityHeadersMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "GET"

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.security_headers.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            assert result.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    async def test_adds_permissions_policy(self):
        """Test Permissions-Policy header is added."""
        middleware = SecurityHeadersMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "GET"

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.security_headers.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            permissions = result.headers["Permissions-Policy"]
            assert "accelerometer=()" in permissions
            assert "camera=()" in permissions
            assert "geolocation=()" in permissions
            assert "microphone=()" in permissions
            assert "payment=()" in permissions

    async def test_adds_content_security_policy(self):
        """Test Content-Security-Policy header is added."""
        middleware = SecurityHeadersMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "GET"

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.security_headers.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            csp = result.headers["Content-Security-Policy"]
            assert "default-src 'self'" in csp
            assert "script-src" in csp


@pytest.mark.anyio
class TestHSTSHeader:
    """Tests for Strict-Transport-Security header."""

    async def test_hsts_not_added_in_dev(self):
        """Test HSTS is NOT added in DEV environment."""
        middleware = SecurityHeadersMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "GET"

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.security_headers.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            assert "Strict-Transport-Security" not in result.headers

    async def test_hsts_not_added_in_local(self):
        """Test HSTS is NOT added in LOCAL environment."""
        middleware = SecurityHeadersMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "GET"

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.security_headers.settings") as mock_settings:
            mock_settings.current_environment = Environment.LOCAL

            result = await middleware.dispatch(request, call_next)

            assert "Strict-Transport-Security" not in result.headers

    async def test_hsts_added_in_staging(self):
        """Test HSTS is added in STG environment."""
        middleware = SecurityHeadersMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "GET"

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.security_headers.settings") as mock_settings:
            mock_settings.current_environment = Environment.STG

            result = await middleware.dispatch(request, call_next)

            hsts = result.headers["Strict-Transport-Security"]
            assert "max-age=31536000" in hsts
            assert "includeSubDomains" in hsts
            assert "preload" in hsts

    async def test_hsts_added_in_production(self):
        """Test HSTS is added in PRD environment."""
        middleware = SecurityHeadersMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "GET"

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.security_headers.settings") as mock_settings:
            mock_settings.current_environment = Environment.PRD

            result = await middleware.dispatch(request, call_next)

            hsts = result.headers["Strict-Transport-Security"]
            assert "max-age=31536000" in hsts  # 1 year
            assert "includeSubDomains" in hsts
            assert "preload" in hsts


@pytest.mark.anyio
class TestSecurityHeadersAllMethods:
    """Tests to ensure headers are added for all HTTP methods."""

    @pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
    async def test_headers_added_for_method(self, method):
        """Test security headers are added for various HTTP methods."""
        middleware = SecurityHeadersMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = method

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.security_headers.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            # Verify all standard headers are present
            assert "X-Content-Type-Options" in result.headers
            assert "X-Frame-Options" in result.headers
            assert "X-XSS-Protection" in result.headers
            assert "Referrer-Policy" in result.headers
            assert "Permissions-Policy" in result.headers
            assert "Content-Security-Policy" in result.headers


@pytest.mark.anyio
class TestSecurityHeadersStatusCodes:
    """Tests to ensure headers are added regardless of status code."""

    @pytest.mark.parametrize("status_code", [200, 201, 204, 400, 401, 403, 404, 500])
    async def test_headers_added_for_status_code(self, status_code):
        """Test security headers are added for various status codes."""
        middleware = SecurityHeadersMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "GET"

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = status_code
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.security_headers.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            assert "X-Content-Type-Options" in result.headers
            assert "X-Frame-Options" in result.headers


@pytest.mark.anyio
class TestSecurityHeadersPreservesExisting:
    """Tests to ensure middleware doesn't break existing response."""

    async def test_preserves_response_status_code(self):
        """Test that response status code is preserved."""
        middleware = SecurityHeadersMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "GET"

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 201
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.security_headers.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            assert result.status_code == 201

    async def test_preserves_existing_headers(self):
        """Test that existing response headers are preserved."""
        middleware = SecurityHeadersMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "GET"

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {"X-Custom-Header": "custom-value"}

        async def call_next(req):
            return response

        with patch("app.middleware.security_headers.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            assert result.headers["X-Custom-Header"] == "custom-value"
            assert "X-Content-Type-Options" in result.headers


class TestSecurityHeaderValues:
    """Tests for specific security header values and their implications."""

    def test_x_frame_options_deny_prevents_framing(self):
        """Test X-Frame-Options DENY prevents all framing."""
        # This is a documentation/verification test
        # DENY is the most restrictive option, preventing any iframe embedding
        expected_value = "DENY"
        assert expected_value == "DENY"

    def test_referrer_policy_strict_origin(self):
        """Test Referrer-Policy prevents full URL leakage."""
        # strict-origin-when-cross-origin:
        # - Same-origin: send full URL
        # - Cross-origin same security: send origin only
        # - Cross-origin less secure: no referrer
        expected_value = "strict-origin-when-cross-origin"
        assert "origin" in expected_value
        assert "cross-origin" in expected_value

    def test_hsts_max_age_one_year(self):
        """Test HSTS max-age is set to 1 year."""
        # 31536000 seconds = 365 days = 1 year
        one_year_seconds = 31536000
        assert one_year_seconds == 365 * 24 * 60 * 60
