from .base import ServiceException
from .auth import (
    DuplicateResourceError,
    ResourceNotFoundError,
    ValidationError,
)
from .email import (
    EmailConfigurationError,
    EmailProviderError,
    EmailSendFailedError,
    EmailTemplateError,
    EmailValidationError,
)

__all__ = [
    "DuplicateResourceError",
    "EmailConfigurationError",
    "EmailProviderError",
    "EmailSendFailedError",
    "EmailTemplateError",
    "EmailValidationError",
    "ResourceNotFoundError",
    "ServiceException",
    "ValidationError",
]
