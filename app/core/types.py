from typing import TypedDict


class RateLimitInfoDict(TypedDict):
    """Rate limit information for headers."""

    limit: int
    remaining: int
    reset_time: int
    window: int
