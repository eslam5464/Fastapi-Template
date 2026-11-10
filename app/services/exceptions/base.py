class ServiceException(Exception):
    """Base exception for service layer errors."""


class ValidationError(ServiceException):
    """A business rule or an input check failed in the service layer."""


class ResourceNotFoundError(ServiceException):
    """A resource the operation needs does not exist."""


class DuplicateResourceError(ServiceException):
    """The resource to create already exists."""
