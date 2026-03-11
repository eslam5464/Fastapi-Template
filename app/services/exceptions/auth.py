from app.services.exceptions.base import ServiceException


class ValidationError(ServiceException):
    """Authentication validation failure in service layer."""


class ResourceNotFoundError(ServiceException):
    """Resource required by auth flow does not exist."""


class DuplicateResourceError(ServiceException):
    """Attempted to create an existing auth resource."""
