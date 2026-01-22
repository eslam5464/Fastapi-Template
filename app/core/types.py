from typing import TypedDict


class TokenPairDict(TypedDict):
    """Internal token pair data passed between auth functions."""

    access_token: str
    refresh_token: str


class TokenWithJtiDict(TypedDict):
    """Token with its JTI for revocation tracking."""

    token: str
    jti: str


class JWTPayloadDict(TypedDict, total=False):
    """JWT payload structure for encoding/decoding."""

    sub: str  # Subject (user ID)
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    type: str  # Token type: "access" or "refresh"
    jti: str  # JWT ID for revocation


class RateLimitInfoDict(TypedDict):
    """Rate limit information for headers."""

    limit: int
    remaining: int
    reset_time: int
    window: int
