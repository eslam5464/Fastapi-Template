from fastapi import APIRouter, Depends

from app.api.v1.deps.auth import get_current_user

# --- FEATURE[redis_rate_limit] START ---
from app.api.v1.deps.rate_limit import RATE_LIMIT_AUTH_RESPONSES, rate_limit_auth

# --- FEATURE[redis_rate_limit] END ---
from app.api.v1.endpoints import auth, user

api_v1_router = APIRouter()


api_v1_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"],
    # --- FEATURE[redis_rate_limit] START ---
    dependencies=[Depends(rate_limit_auth)],
    responses=RATE_LIMIT_AUTH_RESPONSES,
    # --- FEATURE[redis_rate_limit] END ---
)

api_v1_router.include_router(
    user.router,
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(get_current_user)],
)
