from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from loguru import logger
from starlette.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import Environment, settings
from app.core.logger import cleanup_logging, configure_logging
from app.middleware.logging import LoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""

    logger.info("Initializing resources...")
    await configure_logging()
    logger.success("Resources initialized.")

    yield  # Application runs here

    logger.info("Cleaning up resources...")
    await cleanup_logging()
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
