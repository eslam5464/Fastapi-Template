from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI

import app.main as main_module
from app.core.config import Environment
from app.main import (
    ALLOWED_ENVIRONMENTS,
    _check_dependencies,
    _shutdown_dependencies,
    app,
    lifespan,
)
from tests.utils import mock_lifespan_steps


@pytest.mark.anyio
class TestDependencySteps:
    """_check_dependencies / _shutdown_dependencies run each service's step."""

    async def test_check_dependencies_runs_every_check(self, monkeypatch):
        mocks = mock_lifespan_steps(monkeypatch, main_module)

        await _check_dependencies()

        for name, mock in mocks.items():
            if name.startswith("_check_"):
                mock.assert_awaited_once()

    async def test_shutdown_dependencies_runs_every_close(self, monkeypatch):
        mocks = mock_lifespan_steps(monkeypatch, main_module)

        await _shutdown_dependencies()

        for name, mock in mocks.items():
            if name.startswith("_close_"):
                mock.assert_awaited_once()


@pytest.mark.anyio
class TestLifespan:
    """Test lifespan context manager."""

    async def test_lifespan_startup_success(self):
        """Test successful startup sequence."""
        test_app = FastAPI()

        with patch("app.main.setup_logger") as mock_setup_logger:
            with patch("app.main.configure_uvicorn_logging") as mock_configure:
                with patch("app.main._check_dependencies", new_callable=AsyncMock) as mock_check:
                    with patch("app.main.shutdown_logger") as mock_shutdown_logger:
                        with patch("app.main._shutdown_dependencies", new_callable=AsyncMock) as mock_shutdown:
                            async with lifespan(test_app):
                                # Verify startup sequence
                                mock_setup_logger.assert_called_once()
                                mock_configure.assert_called_once()
                                mock_check.assert_called_once()

                            # Verify shutdown sequence
                            mock_shutdown_logger.assert_called_once()
                            mock_shutdown.assert_called_once()

    async def test_lifespan_startup_failure(self):
        """Test that startup failure is propagated."""
        test_app = FastAPI()

        with patch("app.main.setup_logger"):
            with patch("app.main.configure_uvicorn_logging"):
                with patch("app.main._check_dependencies", new_callable=AsyncMock) as mock_check:
                    mock_check.side_effect = RuntimeError("Dependency check failed")

                    with pytest.raises(RuntimeError, match="Dependency check failed"):
                        async with lifespan(test_app):
                            pass

    async def test_lifespan_shutdown(self):
        """Test shutdown sequence after successful startup."""
        test_app = FastAPI()

        with patch("app.main.setup_logger"):
            with patch("app.main.configure_uvicorn_logging"):
                with patch("app.main._check_dependencies", new_callable=AsyncMock):
                    with patch("app.main.shutdown_logger") as mock_shutdown_logger:
                        with patch("app.main._shutdown_dependencies", new_callable=AsyncMock) as mock_shutdown:
                            async with lifespan(test_app):
                                pass

                            # After context exit, shutdown should be called
                            mock_shutdown_logger.assert_called_once()
                            mock_shutdown.assert_called_once()

    async def test_lifespan_calls_in_correct_order(self):
        """Test that lifespan calls happen in correct order."""
        test_app = FastAPI()
        call_order = []

        def track_setup_logger():
            call_order.append("setup_logger")

        def track_configure():
            call_order.append("configure_uvicorn")

        async def track_check():
            call_order.append("check_dependencies")

        def track_shutdown_logger():
            call_order.append("shutdown_logger")

        async def track_shutdown():
            call_order.append("shutdown_dependencies")

        with patch("app.main.setup_logger", side_effect=track_setup_logger):
            with patch("app.main.configure_uvicorn_logging", side_effect=track_configure):
                with patch("app.main._check_dependencies", new_callable=AsyncMock, side_effect=track_check):
                    with patch("app.main.shutdown_logger", side_effect=track_shutdown_logger):
                        with patch(
                            "app.main._shutdown_dependencies",
                            new_callable=AsyncMock,
                            side_effect=track_shutdown,
                        ):
                            async with lifespan(test_app):
                                pass

        # Verify correct order
        assert call_order == [
            "setup_logger",
            "configure_uvicorn",
            "check_dependencies",
            "shutdown_logger",
            "shutdown_dependencies",
        ]


class TestAppConfiguration:
    """Test FastAPI app configuration."""

    def test_app_openapi_enabled_local(self):
        """Test that OpenAPI is enabled in LOCAL environment."""
        assert Environment.LOCAL in ALLOWED_ENVIRONMENTS

    def test_app_openapi_enabled_dev(self):
        """Test that OpenAPI is enabled in DEV environment."""
        assert Environment.DEV in ALLOWED_ENVIRONMENTS

    def test_app_openapi_enabled_stg(self):
        """Test that OpenAPI is enabled in STG environment."""
        assert Environment.STG in ALLOWED_ENVIRONMENTS

    def test_app_openapi_disabled_prod(self):
        """Test that OpenAPI is disabled in PRODUCTION environment."""
        assert Environment.PRD not in ALLOWED_ENVIRONMENTS

    def test_app_has_title(self):
        """Test that app has correct title."""
        assert app.title is not None
        assert isinstance(app.title, str)

    def test_app_has_version(self):
        """Test that app has version."""
        assert app.version is not None
        assert isinstance(app.version, str)

    def test_app_has_description(self):
        """Test that app has description."""
        assert app.description is not None
        assert isinstance(app.description, str)

    def test_app_lifespan_configured(self):
        """Test that app lifespan is configured."""
        # The lifespan should be set
        assert app.router.lifespan_context is not None

    def test_app_middleware_registered(self):
        """Test that middleware is registered."""
        # Check that middleware stack is not empty
        assert len(app.user_middleware) > 0

        # Verify specific middleware types
        middleware_types = [m.cls.__name__ for m in app.user_middleware]

        # Should have CORS middleware
        assert "CORSMiddleware" in middleware_types

        # Should have custom middleware
        assert "LoggingMiddleware" in middleware_types

    def test_app_router_included(self):
        """Test that API router is included."""
        # FastAPI 0.162+ wraps include_router() routes in a lazy _IncludedRouter
        # with no `path`, so the root routes are read from the OpenAPI schema
        # and only the mounted sub-apps are read from app.routes.
        assert "/health" in app.openapi()["paths"]
        routes = [route.path for route in app.routes if hasattr(route, "path")]

        # Should have mounted versioned apps
        assert "/v1" in routes
        # --- FEATURE[api_v2] START ---
        assert "/v2" in routes
        # --- FEATURE[api_v2] END ---

    def test_app_cors_configuration(self):
        """Test CORS middleware configuration."""
        # Find CORS middleware
        cors_middleware = None
        for middleware in app.user_middleware:
            if middleware.cls.__name__ == "CORSMiddleware":
                cors_middleware = middleware
                break

        # Verify CORS middleware is configured
        assert cors_middleware is not None

    def test_app_openapi_url_conditional(self):
        """Test that OpenAPI URL is conditionally set based on environment."""
        with patch("app.main.settings.current_environment", Environment.LOCAL):
            # In LOCAL, should be enabled
            from app.main import ALLOWED_ENVIRONMENTS

            assert Environment.LOCAL in ALLOWED_ENVIRONMENTS

        with patch("app.main.settings.current_environment", Environment.PRD):
            # In PRODUCTION, should be disabled
            assert Environment.PRD not in ALLOWED_ENVIRONMENTS


@pytest.mark.anyio
class TestAppEndpoints:
    """Integration tests for root and versioned docs endpoints."""

    async def test_health_endpoint_is_unversioned(self, client):
        """Healthcheck should remain available at root path."""
        response = await client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    async def test_root_docs_endpoints_are_disabled(self, client):
        """Root docs endpoints should not be exposed after versioned split."""
        docs_paths = ["/docs", "/redoc", "/openapi.json"]

        for path in docs_paths:
            response = await client.get(path)
            assert response.status_code == 404

    async def test_v1_docs_endpoints_are_available_in_allowed_envs(self, client):
        """Mounted v1 app should expose its own docs endpoints in allowed envs."""
        if app.openapi_url is None and Environment.LOCAL not in ALLOWED_ENVIRONMENTS:
            pytest.skip("Docs are disabled in this environment")

        docs_paths = ["/v1/docs", "/v1/redoc", "/v1/openapi.json"]
        for path in docs_paths:
            response = await client.get(path)
            assert response.status_code == 200

    # --- FEATURE[api_v2] START ---
    async def test_v2_docs_endpoints_are_available_in_allowed_envs(self, client):
        """Mounted v2 app should expose its own docs endpoints in allowed envs."""
        if app.openapi_url is None and Environment.LOCAL not in ALLOWED_ENVIRONMENTS:
            pytest.skip("Docs are disabled in this environment")

        docs_paths = ["/v2/docs", "/v2/redoc", "/v2/openapi.json"]
        for path in docs_paths:
            response = await client.get(path)
            assert response.status_code == 200

    # --- FEATURE[api_v2] END ---


@pytest.mark.anyio
class TestTrustedHostMiddleware:
    """Integration tests for the TrustedHostMiddleware host allowlist."""

    async def test_allowed_host_gets_through(self, client):
        """A request whose Host header is in ALLOWED_HOSTS reaches the app."""
        response = await client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    async def test_disallowed_host_gets_400(self, client):
        """A request whose Host header is not in ALLOWED_HOSTS is rejected with HTTP 400."""
        response = await client.get("/health", headers={"Host": "evil.example.com"})

        assert response.status_code == 400
