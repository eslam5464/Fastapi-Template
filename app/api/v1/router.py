from fastapi import APIRouter, Depends

from app.api.v1.deps.auth import get_current_user
from app.api.v1.deps.rate_limit import RATE_LIMIT_AUTH_RESPONSES, rate_limit_auth
from app.api.v1.endpoints import auth, user

api_v1_router = APIRouter()


api_v1_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"],
    dependencies=[Depends(rate_limit_auth)],
    responses=RATE_LIMIT_AUTH_RESPONSES,
)

api_v1_router.include_router(
    user.router,
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(get_current_user)],
)
