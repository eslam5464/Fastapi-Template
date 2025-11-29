from app.core.exceptions.base import CustomException


class RateLimiterException(CustomException):
    """
    Base exception for Rate Limiter
    """

    def __init__(self, message, exception: Exception | None = None):
        super().__init__(message, exception)


class RateLimitExceeded(RateLimiterException):
    """
    Rate limit exceeded for a key
    """

    def __init__(self, message, exception: Exception | None = None):
        super().__init__(message, exception)


class RateLimitConfigurationError(RateLimiterException):
    """
    Invalid rate limit configuration
    """

    def __init__(self, message, exception: Exception | None = None):
        super().__init__(message, exception)


class RateLimitKeyGenerationError(RateLimiterException):
    """
    Error generating rate limit key
    """

    def __init__(self, message, exception: Exception | None = None):
        super().__init__(message, exception)
