from fastapi import APIRouter, Depends, status

from app.api.v1.deps.auth import get_current_user
from app.api.v1.deps.rate_limit import rate_limit_auth
from app.api.v1.endpoints import auth, user
from app.core import responses

api_v1_router = APIRouter(prefix="/api/v1")


api_v1_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Auth"],
    dependencies=([Depends(rate_limit_auth)]),
    responses={
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "model": responses.TooManyRequestsResponse,
            "headers": {
                "X-RateLimit-Limit": {
                    "description": "Maximum requests allowed (10/min)",
                    "schema": {"type": "integer", "example": 10},
                },
                "X-RateLimit-Remaining": {
                    "description": "Requests remaining in current window",
                    "schema": {"type": "integer", "example": 9},
                },
                "X-RateLimit-Reset": {
                    "description": "Unix timestamp when limit resets",
                    "schema": {"type": "integer", "example": 17655251150102866},
                },
            },
        },
    },
)

api_v1_router.include_router(
    user.router,
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(get_current_user)],
)
