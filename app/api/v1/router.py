from fastapi import APIRouter
from app.api.v1.endpoints import user, auth

api_v1_router = APIRouter(prefix="/v1")


api_v1_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"],
)

api_v1_router.include_router(
    user.router,
    prefix="/users",
    tags=["Users"],
)
