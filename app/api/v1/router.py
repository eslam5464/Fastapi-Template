from fastapi import APIRouter, Depends

from app.api.v1.deps.auth import get_current_user
from app.api.v1.endpoints import auth, user

api_v1_router = APIRouter(prefix="/api/v1")


api_v1_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"],
)

api_v1_router.include_router(
    user.router,
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(get_current_user)],
)
