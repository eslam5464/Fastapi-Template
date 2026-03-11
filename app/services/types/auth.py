from typing import TypedDict


class TokenPairDict(TypedDict):
    """Internal token pair data passed between auth flows."""

    access_token: str
    refresh_token: str


class TokenWithJtiDict(TypedDict):
    """Encoded token plus JTI for revocation tracking."""

    token: str
    jti: str


class JWTPayloadDict(TypedDict, total=False):
    """JWT payload structure for auth token encoding/decoding."""

    sub: str
    exp: int
    iat: int
    type: str
    jti: str


class LogoutRevokePayloadDict(TypedDict):
    """Payload used to revoke a token from blacklist storage."""

    jti: str
    ttl_seconds: int
