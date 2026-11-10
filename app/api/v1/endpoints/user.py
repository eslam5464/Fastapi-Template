from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.deps.auth import get_current_user

# --- FEATURE[redis_rate_limit] START ---
from app.api.v1.deps.rate_limit import create_rate_limit_user_and_ip, rate_limit_responses

# --- FEATURE[redis_rate_limit] END ---
from app.core import responses
from app.models import User
from app.schemas import UserResponse

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": responses.UnauthorizedResponse},
        # --- FEATURE[redis_rate_limit] START ---
        **rate_limit_responses(limit=60),
        # --- FEATURE[redis_rate_limit] END ---
    },
    # --- FEATURE[redis_rate_limit] START ---
    dependencies=[Depends(create_rate_limit_user_and_ip(limit=60, window=60, prefix="users:me:get"))],
    # --- FEATURE[redis_rate_limit] END ---
    summary="Read current user",
    description="Get the details of the currently authenticated user.",
)
async def read_user_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user
