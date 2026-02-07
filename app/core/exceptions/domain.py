from app.core.exceptions.base import AppException

# =============================================================================
# Generic Domain Exceptions (raised by Services, caught by Deps)
# =============================================================================


class ValidationError(AppException):
    """Business rule validation failure."""

    def __init__(self, message: str = "Validation failed", exception: Exception | None = None):
        super().__init__(message, exception)


class ResourceNotFoundError(AppException):
    """Requested resource does not exist."""

    def __init__(self, message: str = "Resource not found", exception: Exception | None = None):
        super().__init__(message, exception)


class ProcessingError(AppException):
    """Error during business logic processing."""

    def __init__(self, message: str = "Processing failed", exception: Exception | None = None):
        super().__init__(message, exception)


class DuplicateResourceError(AppException):
    """Attempted to create a resource that already exists."""

    def __init__(
        self, message: str = "Resource already exists", exception: Exception | None = None
    ):
        super().__init__(message, exception)
