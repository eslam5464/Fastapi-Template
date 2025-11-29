from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.deps.auth import get_current_user
from app.api.v1.deps.rate_limit import create_rate_limit_user_and_ip
from app.core import responses
from app.models import User
from app.schemas import UserResponse

router = APIRouter()


@router.get(
    "/me",
    response_model=UserResponse,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": responses.UnauthorizedResponse},
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": responses.TooManyRequestsResponse,
            "headers": {
                "X-RateLimit-Limit": {
                    "description": "Maximum requests allowed (60/min)",
                    "schema": {"type": "integer", "example": 60},
                },
                "X-RateLimit-Remaining": {
                    "description": "Requests remaining in current window",
                    "schema": {"type": "integer", "example": 59},
                },
                "X-RateLimit-Reset": {
                    "description": "Unix timestamp when limit resets",
                    "schema": {"type": "integer", "example": 1764425820102866},
                },
            },
        },
    },
    dependencies=(
        [Depends(create_rate_limit_user_and_ip(limit=60, window=60, prefix="users:me:get"))]
    ),
    summary="Read current user",
    description="Get the details of the currently authenticated user.",
)
async def read_user_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user
