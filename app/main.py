from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.routes import api_router
from app.core.config import Environment, settings
from app.core.logger import configure_uvicorn_logging, setup_logger, shutdown_logger
from app.middleware.logging import LoggingMiddleware
from app.services.cache.manager import cache_manager


async def _check_dependencies():
    """Check essential dependencies before starting the app"""

    is_healthy = await cache_manager.health_check()

    if not is_healthy:
        logger.error("CacheManager health check failed. Exiting application.")
        raise RuntimeError("CacheManager is not healthy.")

    logger.success("CacheManager is healthy.")


async def _shutdown_dependencies():
    """Shutdown essential dependencies gracefully"""

    await cache_manager.close()
    logger.success("CacheManager connection closed.")


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
    openapi_url=("/openapi.json" if settings.current_environment in ALLOWED_ENVIRONMENTS else None),
    docs_url="/docs" if settings.current_environment in ALLOWED_ENVIRONMENTS else None,
    redoc_url="/redoc" if settings.current_environment in ALLOWED_ENVIRONMENTS else None,
    lifespan=lifespan,
    generate_unique_id_function=lambda route: f"{route.tags[0]}-{route.name}",
)

# Set CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set logging middleware
app.add_middleware(LoggingMiddleware)

# Include API router
app.include_router(api_router)
