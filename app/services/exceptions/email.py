from app.services.exceptions.base import ServiceException


class EmailValidationError(ServiceException):
    """Raised when an email payload violates service-layer validation rules."""


class EmailTemplateError(ServiceException):
    """Raised when template data is invalid or incompatible with payload content."""


class EmailConfigurationError(ServiceException):
    """Raised when required provider configuration is missing or invalid."""


class EmailProviderError(ServiceException):
    """Raised when an email provider responds with an invalid or unexpected payload."""


class EmailSendFailedError(ServiceException):
    """Raised when an email provider call fails during send execution."""
