from fastapi import APIRouter

from app.api.v1.router import api_v1_router
from app.schemas.health_check import HealthCheckResponse

api_router = APIRouter()


@api_router.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["Health"],
    summary="Health Check",
)
async def health_check():
    return {"status": "healthy"}


api_router.include_router(
    api_v1_router,
)
