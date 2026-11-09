from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from loguru import logger

from app.api.routes import api_router
from app.api.v1.router import api_v1_router
from app.api.v2.router import api_v2_router
from app.core.config import Environment, settings
from app.core.logger import configure_uvicorn_logging, setup_logger, shutdown_logger
from app.middleware.csrf import CSRFMiddleware
from app.middleware.logging import LoggingMiddleware

# --- FEATURE[redis_rate_limit] START ---
from app.middleware.rate_limit import RateLimitHeaderMiddleware

# --- FEATURE[redis_rate_limit] END ---
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.services.cache.manager import cache_manager

# --- FEATURE[redis_rate_limit] START ---
from app.services.cache.rate_limiter import rate_limiter

# --- FEATURE[redis_rate_limit] END ---
# --- FEATURE[redis_token_blacklist] START ---
from app.services.cache.token_blacklist import token_blacklist

# --- FEATURE[redis_token_blacklist] END ---


async def _check_cache_manager() -> None:
    """Fail startup when caching is enabled but the cache store is not reachable."""
    cache_healthy = await cache_manager.health_check()

    if not cache_healthy and settings.cache_enabled:
        logger.error("CacheManager health check failed. Exiting application.")
        raise RuntimeError("CacheManager is not healthy.")
    else:
        logger.success("CacheManager is healthy.")


# --- FEATURE[redis_rate_limit] START ---
async def _check_rate_limiter() -> None:
    """Fail startup when rate limiting is enabled but its store is not reachable."""
    rate_limiter_healthy = await rate_limiter.health_check()

    if not rate_limiter_healthy and settings.rate_limit_enabled:
        logger.error("RateLimiter health check failed. Exiting application.")
        raise RuntimeError("RateLimiter is not healthy.")
    else:
        logger.success("RateLimiter is healthy.")


# --- FEATURE[redis_rate_limit] END ---


# --- FEATURE[redis_token_blacklist] START ---
async def _check_token_blacklist() -> None:
    """Warn (outside LOCAL) when the token blacklist is not reachable; startup continues."""
    if settings.current_environment != Environment.LOCAL:
        blacklist_healthy = await token_blacklist.health_check()

        if not blacklist_healthy:
            logger.warning("TokenBlacklist health check failed. Token revocation may not work.")
        else:
            logger.success("TokenBlacklist is healthy.")


# --- FEATURE[redis_token_blacklist] END ---


async def _check_dependencies():
    """Check essential dependencies before starting the app"""
    await _check_cache_manager()
    # --- FEATURE[redis_rate_limit] START ---
    await _check_rate_limiter()
    # --- FEATURE[redis_rate_limit] END ---
    # --- FEATURE[redis_token_blacklist] START ---
    await _check_token_blacklist()
    # --- FEATURE[redis_token_blacklist] END ---


async def _close_cache_manager() -> None:
    await cache_manager.close()
    logger.success("CacheManager connection closed.")


# --- FEATURE[redis_rate_limit] START ---
async def _close_rate_limiter() -> None:
    await rate_limiter.close()
    logger.success("RateLimiter connection closed.")


# --- FEATURE[redis_rate_limit] END ---


# --- FEATURE[redis_token_blacklist] START ---
async def _close_token_blacklist() -> None:
    await token_blacklist.close()
    logger.success("TokenBlacklist connection closed.")


# --- FEATURE[redis_token_blacklist] END ---


async def _shutdown_dependencies():
    """Shutdown essential dependencies gracefully"""
    await _close_cache_manager()
    # --- FEATURE[redis_rate_limit] START ---
    await _close_rate_limiter()
    # --- FEATURE[redis_rate_limit] END ---
    # --- FEATURE[redis_token_blacklist] START ---
    await _close_token_blacklist()
    # --- FEATURE[redis_token_blacklist] END ---


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""

    setup_logger()
    configure_uvicorn_logging()

    logger.info("Initializing resources...")
    await _check_dependencies()
    logger.success("Resources initialized.")

    yield  # Application runs here

    logger.info("Cleaning up resources...")
    shutdown_logger()
    await _shutdown_dependencies()
    logger.success("Resources cleaned up.")


ALLOWED_ENVIRONMENTS = {Environment.LOCAL, Environment.DEV, Environment.STG}

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=settings.app_description,
    openapi_url=None,
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
    generate_unique_id_function=lambda route: f"{route.tags[0]}-{route.name}",
)


def _create_versioned_app(version: str) -> FastAPI:
    """Create a mounted FastAPI sub-app with version-specific docs endpoints."""
    docs_enabled = settings.current_environment in ALLOWED_ENVIRONMENTS
    return FastAPI(
        title=f"{settings.app_title} {version.upper()}",
        version=settings.app_version,
        description=settings.app_description,
        openapi_url="/openapi.json" if docs_enabled else None,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        generate_unique_id_function=lambda route: f"{route.tags[0]}-{route.name}",
    )


v1_app = _create_versioned_app("v1")
v1_app.include_router(api_v1_router)

v2_app = _create_versioned_app("v2")
v2_app.include_router(api_v2_router)

# Set CORS middleware with restricted configuration
# Reference: https://cheatsheetseries.owasp.org/cheatsheets/REST_Security_Cheat_Sheet.html
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-CSRF-Token",
        "X-Request-ID",
        "Accept",
        "Accept-Language",
        "Origin",
    ],
)

# Set security headers middleware (OWASP recommended)
app.add_middleware(SecurityHeadersMiddleware)

# Set CSRF protection middleware (header-based)
app.add_middleware(CSRFMiddleware)

# --- FEATURE[redis_rate_limit] START ---
# Set rate limit header middleware
app.add_middleware(RateLimitHeaderMiddleware)
# --- FEATURE[redis_rate_limit] END ---

# Set logging middleware
app.add_middleware(LoggingMiddleware)

# Set trusted host middleware (added last so it runs outermost): reject requests
# whose Host header is not in ALLOWED_HOSTS before any other middleware runs.
# Never falls back to "*" - the allowlist comes straight from configuration.
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts_list)

# Include API router
app.include_router(api_router)

# Mount versioned API apps
app.mount("/v1", v1_app)
app.mount("/v2", v2_app)
