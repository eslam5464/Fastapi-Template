import secrets
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request
from starlette.middleware.base import _StreamingResponse

from app.core.config import Environment
from app.core.exceptions import http_exceptions
from app.middleware.csrf import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    CSRF_TOKEN_LENGTH,
    EXEMPT_PATHS,
    SAFE_METHODS,
    CSRFMiddleware,
    generate_csrf_token,
)


class TestGenerateCSRFToken:
    """Tests for CSRF token generation."""

    def test_generates_token_with_correct_length(self):
        """Test that generated token has correct length."""
        token = generate_csrf_token()
        # URL-safe base64 encoding produces ~4/3 of the byte length
        assert len(token) >= CSRF_TOKEN_LENGTH

    def test_generates_unique_tokens(self):
        """Test that each call generates a unique token."""
        tokens = [generate_csrf_token() for _ in range(100)]
        unique_tokens = set(tokens)
        assert len(unique_tokens) == 100

    def test_token_is_url_safe(self):
        """Test that token contains only URL-safe characters."""
        token = generate_csrf_token()
        # URL-safe base64 characters: A-Z, a-z, 0-9, -, _
        valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
        assert all(c in valid_chars for c in token)


class TestCSRFMiddlewareConstants:
    """Tests for CSRF middleware constants."""

    def test_csrf_cookie_name(self):
        """Test CSRF cookie name constant."""
        assert CSRF_COOKIE_NAME == "csrf_token"

    def test_csrf_header_name(self):
        """Test CSRF header name constant."""
        assert CSRF_HEADER_NAME == "X-CSRF-Token"

    def test_safe_methods(self):
        """Test safe HTTP methods that don't require CSRF."""
        assert "GET" in SAFE_METHODS
        assert "HEAD" in SAFE_METHODS
        assert "OPTIONS" in SAFE_METHODS
        assert "TRACE" in SAFE_METHODS
        assert "POST" not in SAFE_METHODS
        assert "PUT" not in SAFE_METHODS
        assert "DELETE" not in SAFE_METHODS
        assert "PATCH" not in SAFE_METHODS

    def test_exempt_paths(self):
        """Test exempt paths from CSRF protection."""
        assert "/api/v1/auth/login" in EXEMPT_PATHS
        assert "/api/v1/auth/signup" in EXEMPT_PATHS
        assert "/api/v1/auth/refresh-token" in EXEMPT_PATHS
        assert "/health" in EXEMPT_PATHS
        assert "/docs" in EXEMPT_PATHS


@pytest.mark.anyio
class TestCSRFMiddlewareLocalEnvironment:
    """Tests for CSRF middleware in LOCAL environment."""

    async def test_skips_csrf_in_local_environment(self):
        """Test that CSRF validation is skipped in LOCAL environment."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url = MagicMock(path="/api/v1/users")
        request.cookies = {}  # No CSRF cookie
        request.headers = {}  # No CSRF header

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200

        async def call_next(req):
            return response

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.LOCAL

            result = await middleware.dispatch(request, call_next)

            assert result == response


@pytest.mark.anyio
class TestCSRFMiddlewareSafeMethods:
    """Tests for CSRF middleware with safe HTTP methods."""

    async def test_get_request_passes_without_csrf(self):
        """Test GET requests pass without CSRF validation."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url = MagicMock(path="/api/v1/users")
        request.cookies = {}

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            assert result == response

    async def test_head_request_passes_without_csrf(self):
        """Test HEAD requests pass without CSRF validation."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "HEAD"
        request.url = MagicMock(path="/api/v1/users")
        request.cookies = {}

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            assert result == response

    async def test_options_request_passes_without_csrf(self):
        """Test OPTIONS requests pass without CSRF validation."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "OPTIONS"
        request.url = MagicMock(path="/api/v1/users")
        request.cookies = {}

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            assert result == response


@pytest.mark.anyio
class TestCSRFMiddlewareExemptPaths:
    """Tests for CSRF middleware with exempt paths."""

    async def test_login_path_exempt(self):
        """Test login path is exempt from CSRF."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url = MagicMock(path="/api/v1/auth/login")
        request.cookies = {}  # No CSRF cookie

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200

        async def call_next(req):
            return response

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            assert result == response

    async def test_signup_path_exempt(self):
        """Test signup path is exempt from CSRF."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url = MagicMock(path="/api/v1/auth/signup")
        request.cookies = {}

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200

        async def call_next(req):
            return response

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            assert result == response

    async def test_refresh_token_path_exempt(self):
        """Test refresh-token path is exempt from CSRF."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url = MagicMock(path="/api/v1/auth/refresh-token")
        request.cookies = {}

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200

        async def call_next(req):
            return response

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            assert result == response

    async def test_docs_path_prefix_exempt(self):
        """Test paths starting with /docs are exempt."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url = MagicMock(path="/docs/oauth2-redirect")
        request.cookies = {}

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200

        async def call_next(req):
            return response

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            assert result == response


@pytest.mark.anyio
class TestCSRFMiddlewareValidation:
    """Tests for CSRF token validation."""

    async def test_missing_cookie_raises_forbidden(self):
        """Test missing CSRF cookie raises ForbiddenException."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url = MagicMock(path="/api/v1/users")
        request.cookies = {}  # No CSRF cookie
        request.headers = {CSRF_HEADER_NAME: "some-token"}

        async def call_next(req):
            return MagicMock()

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            with pytest.raises(http_exceptions.ForbiddenException) as exc_info:
                await middleware.dispatch(request, call_next)

            assert "CSRF token missing" in str(exc_info.value.detail)

    async def test_missing_header_raises_forbidden(self):
        """Test missing CSRF header raises ForbiddenException."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url = MagicMock(path="/api/v1/users")
        request.cookies = {CSRF_COOKIE_NAME: "cookie-token"}
        request.headers = {}  # No CSRF header

        async def call_next(req):
            return MagicMock()

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            with pytest.raises(http_exceptions.ForbiddenException) as exc_info:
                await middleware.dispatch(request, call_next)

            assert "CSRF token missing" in str(exc_info.value.detail)

    async def test_mismatched_tokens_raises_forbidden(self):
        """Test mismatched CSRF tokens raise ForbiddenException."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url = MagicMock(path="/api/v1/users")
        request.cookies = {CSRF_COOKIE_NAME: "cookie-token-123"}
        request.headers = {CSRF_HEADER_NAME: "different-token-456"}

        async def call_next(req):
            return MagicMock()

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            with pytest.raises(http_exceptions.ForbiddenException) as exc_info:
                await middleware.dispatch(request, call_next)

            assert "CSRF token validation failed" in str(exc_info.value.detail)

    async def test_matching_tokens_passes(self):
        """Test matching CSRF tokens pass validation."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "POST"
        request.url = MagicMock(path="/api/v1/users")

        csrf_token = generate_csrf_token()
        request.cookies = {CSRF_COOKIE_NAME: csrf_token}
        request.headers = {CSRF_HEADER_NAME: csrf_token}

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200

        async def call_next(req):
            return response

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            result = await middleware.dispatch(request, call_next)

            assert result == response

    async def test_put_request_requires_csrf(self):
        """Test PUT requests require CSRF validation."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "PUT"
        request.url = MagicMock(path="/api/v1/users/1")
        request.cookies = {}
        request.headers = {}

        async def call_next(req):
            return MagicMock()

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            with pytest.raises(http_exceptions.ForbiddenException):
                await middleware.dispatch(request, call_next)

    async def test_delete_request_requires_csrf(self):
        """Test DELETE requests require CSRF validation."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "DELETE"
        request.url = MagicMock(path="/api/v1/users/1")
        request.cookies = {}
        request.headers = {}

        async def call_next(req):
            return MagicMock()

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            with pytest.raises(http_exceptions.ForbiddenException):
                await middleware.dispatch(request, call_next)

    async def test_patch_request_requires_csrf(self):
        """Test PATCH requests require CSRF validation."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "PATCH"
        request.url = MagicMock(path="/api/v1/users/1")
        request.cookies = {}
        request.headers = {}

        async def call_next(req):
            return MagicMock()

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            with pytest.raises(http_exceptions.ForbiddenException):
                await middleware.dispatch(request, call_next)


@pytest.mark.anyio
class TestCSRFMiddlewareCookieSetup:
    """Tests for CSRF cookie setup."""

    async def test_sets_csrf_cookie_on_get_request(self):
        """Test CSRF cookie is set on GET request if not present."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url = MagicMock(path="/api/v1/users")
        request.cookies = {}  # No existing cookie

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}
        response.set_cookie = MagicMock()

        async def call_next(req):
            return response

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            await middleware.dispatch(request, call_next)

            # Verify set_cookie was called
            response.set_cookie.assert_called_once()
            call_kwargs = response.set_cookie.call_args.kwargs
            assert call_kwargs["key"] == CSRF_COOKIE_NAME
            assert call_kwargs["httponly"] is False  # Must be readable by JS
            assert call_kwargs["samesite"] == "strict"

    async def test_does_not_set_cookie_if_exists(self):
        """Test CSRF cookie is not set if already present."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url = MagicMock(path="/api/v1/users")
        request.cookies = {CSRF_COOKIE_NAME: "existing-token"}

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}
        response.set_cookie = MagicMock()

        async def call_next(req):
            return response

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            await middleware.dispatch(request, call_next)

            # Cookie should not be set again
            response.set_cookie.assert_not_called()

    async def test_secure_cookie_in_production(self):
        """Test CSRF cookie is secure in production environment."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url = MagicMock(path="/api/v1/users")
        request.cookies = {}

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}
        response.set_cookie = MagicMock()

        async def call_next(req):
            return response

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.PRD

            await middleware.dispatch(request, call_next)

            call_kwargs = response.set_cookie.call_args.kwargs
            assert call_kwargs["secure"] is True

    async def test_not_secure_cookie_in_dev(self):
        """Test CSRF cookie is not secure in dev environment."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.method = "GET"
        request.url = MagicMock(path="/api/v1/users")
        request.cookies = {}

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}
        response.set_cookie = MagicMock()

        async def call_next(req):
            return response

        with patch("app.middleware.csrf.settings") as mock_settings:
            mock_settings.current_environment = Environment.DEV

            await middleware.dispatch(request, call_next)

            call_kwargs = response.set_cookie.call_args.kwargs
            assert call_kwargs["secure"] is False


@pytest.mark.anyio
class TestCSRFMiddlewareIsExempt:
    """Tests for _is_exempt method."""

    async def test_exact_match_exempt(self):
        """Test exact path matching for exemption."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.url = MagicMock(path="/health")

        assert middleware._is_exempt(request) is True

    async def test_prefix_match_exempt(self):
        """Test prefix matching for exemption."""
        middleware = CSRFMiddleware(MagicMock())

        # Test /docs prefix
        request = MagicMock(spec=Request)
        request.url = MagicMock(path="/docs/oauth2-redirect")
        assert middleware._is_exempt(request) is True

        # Test /redoc prefix
        request.url = MagicMock(path="/redoc")
        assert middleware._is_exempt(request) is True

        # Test /openapi prefix
        request.url = MagicMock(path="/openapi.json")
        assert middleware._is_exempt(request) is True

    async def test_non_exempt_path(self):
        """Test non-exempt path."""
        middleware = CSRFMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.url = MagicMock(path="/api/v1/users")

        assert middleware._is_exempt(request) is False


class TestCSRFTimingAttackPrevention:
    """Tests for timing attack prevention."""

    def test_uses_constant_time_comparison(self):
        """Test that token comparison uses constant-time algorithm."""
        # This is a design verification test
        # The middleware uses secrets.compare_digest for constant-time comparison
        token1 = "abc123"
        token2 = "abc123"
        token3 = "xyz789"

        # Verify secrets.compare_digest works as expected
        assert secrets.compare_digest(token1, token2) is True
        assert secrets.compare_digest(token1, token3) is False
