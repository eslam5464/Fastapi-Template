from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI

from app.core.config import Environment
from app.main import (
    ALLOWED_ENVIRONMENTS,
    _check_dependencies,
    _shutdown_dependencies,
    app,
    lifespan,
)


@pytest.mark.anyio
class TestDependencyChecks:
    """Test dependency health checks on startup."""

    async def test_check_dependencies_all_healthy(self):
        """Test that check passes when all dependencies are healthy."""
        with patch("app.main.cache_manager.health_check", new_callable=AsyncMock) as mock_cache:
            with patch("app.main.rate_limiter.health_check", new_callable=AsyncMock) as mock_rate:
                with patch("app.main.settings.cache_enabled", True):
                    with patch("app.main.settings.rate_limit_enabled", True):
                        mock_cache.return_value = True
                        mock_rate.return_value = True

                        # Should not raise any exception
                        await _check_dependencies()

                        mock_cache.assert_called_once()
                        mock_rate.assert_called_once()

    async def test_check_dependencies_cache_unhealthy_enabled(self):
        """Test that RuntimeError is raised when cache is unhealthy and enabled."""
        with patch("app.main.cache_manager.health_check", new_callable=AsyncMock) as mock_cache:
            with patch("app.main.settings.cache_enabled", True):
                mock_cache.return_value = False

                with pytest.raises(RuntimeError, match="CacheManager is not healthy"):
                    await _check_dependencies()

    async def test_check_dependencies_cache_unhealthy_disabled(self):
        """Test that check continues when cache is unhealthy but disabled."""
        with patch("app.main.cache_manager.health_check", new_callable=AsyncMock) as mock_cache:
            with patch("app.main.rate_limiter.health_check", new_callable=AsyncMock) as mock_rate:
                with patch("app.main.settings.cache_enabled", False):
                    with patch("app.main.settings.rate_limit_enabled", True):
                        mock_cache.return_value = False
                        mock_rate.return_value = True

                        # Should not raise exception
                        await _check_dependencies()

                        # Both checks should still be called
                        mock_cache.assert_called_once()
                        mock_rate.assert_called_once()

    async def test_check_dependencies_rate_limiter_unhealthy_enabled(self):
        """Test that RuntimeError is raised when rate limiter is unhealthy and enabled."""
        with patch("app.main.cache_manager.health_check", new_callable=AsyncMock) as mock_cache:
            with patch("app.main.rate_limiter.health_check", new_callable=AsyncMock) as mock_rate:
                with patch("app.main.settings.cache_enabled", True):
                    with patch("app.main.settings.rate_limit_enabled", True):
                        mock_cache.return_value = True
                        mock_rate.return_value = False

                        with pytest.raises(RuntimeError, match="RateLimiter is not healthy"):
                            await _check_dependencies()

    async def test_check_dependencies_rate_limiter_unhealthy_disabled(self):
        """Test that check continues when rate limiter is unhealthy but disabled."""
        with patch("app.main.cache_manager.health_check", new_callable=AsyncMock) as mock_cache:
            with patch("app.main.rate_limiter.health_check", new_callable=AsyncMock) as mock_rate:
                with patch("app.main.settings.cache_enabled", True):
                    with patch("app.main.settings.rate_limit_enabled", False):
                        mock_cache.return_value = True
                        mock_rate.return_value = False

                        # Should not raise exception
                        await _check_dependencies()

                        mock_cache.assert_called_once()
                        mock_rate.assert_called_once()

    async def test_check_dependencies_both_unhealthy_both_disabled(self):
        """Test that check continues when both are unhealthy but disabled."""
        with patch("app.main.cache_manager.health_check", new_callable=AsyncMock) as mock_cache:
            with patch("app.main.rate_limiter.health_check", new_callable=AsyncMock) as mock_rate:
                with patch("app.main.settings.cache_enabled", False):
                    with patch("app.main.settings.rate_limit_enabled", False):
                        mock_cache.return_value = False
                        mock_rate.return_value = False

                        # Should not raise exception
                        await _check_dependencies()

                        mock_cache.assert_called_once()
                        mock_rate.assert_called_once()


@pytest.mark.anyio
class TestShutdown:
    """Test shutdown dependencies function."""

    async def test_shutdown_dependencies_closes_cache(self):
        """Test that shutdown closes cache manager."""
        with patch("app.main.cache_manager.close", new_callable=AsyncMock) as mock_cache_close:
            with patch("app.main.rate_limiter.close", new_callable=AsyncMock) as mock_rate_close:
                await _shutdown_dependencies()

                mock_cache_close.assert_called_once()
                mock_rate_close.assert_called_once()

    async def test_shutdown_dependencies_closes_rate_limiter(self):
        """Test that shutdown closes rate limiter."""
        with patch("app.main.cache_manager.close", new_callable=AsyncMock) as mock_cache_close:
            with patch("app.main.rate_limiter.close", new_callable=AsyncMock) as mock_rate_close:
                await _shutdown_dependencies()

                mock_cache_close.assert_called_once()
                mock_rate_close.assert_called_once()

    async def test_shutdown_dependencies_handles_exceptions(self):
        """Test that shutdown handles exceptions gracefully."""
        with patch("app.main.cache_manager.close", new_callable=AsyncMock) as mock_cache_close:
            with patch("app.main.rate_limiter.close", new_callable=AsyncMock) as mock_rate_close:
                # Simulate cache close failing
                mock_cache_close.side_effect = Exception("Cache close failed")

                # Should raise the exception (not swallowed)
                with pytest.raises(Exception, match="Cache close failed"):
                    await _shutdown_dependencies()


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
                        with patch(
                            "app.main._shutdown_dependencies", new_callable=AsyncMock
                        ) as mock_shutdown:
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
                        with patch(
                            "app.main._shutdown_dependencies", new_callable=AsyncMock
                        ) as mock_shutdown:
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
                with patch(
                    "app.main._check_dependencies", new_callable=AsyncMock, side_effect=track_check
                ):
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
        assert "RateLimitHeaderMiddleware" in middleware_types
        assert "LoggingMiddleware" in middleware_types

    def test_app_router_included(self):
        """Test that API router is included."""
        # Check that routes are registered
        routes = [route.path for route in app.routes]

        # Should have API routes
        assert any("/api/" in route for route in routes)

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
