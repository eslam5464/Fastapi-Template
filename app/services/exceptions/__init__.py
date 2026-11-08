from .base import ServiceException
from .auth import (
    DuplicateResourceError,
    ResourceNotFoundError,
    ValidationError,
)

# --- FEATURE[resend|brevo] START ---
from .email import (
    EmailConfigurationError,
    EmailProviderError,
    EmailSendFailedError,
    EmailTemplateError,
    EmailValidationError,
)
# --- FEATURE[resend|brevo] END ---

__all__ = [
    "DuplicateResourceError",
    # --- FEATURE[resend|brevo] START ---
    "EmailConfigurationError",
    "EmailProviderError",
    "EmailSendFailedError",
    "EmailTemplateError",
    "EmailValidationError",
    # --- FEATURE[resend|brevo] END ---
    "ResourceNotFoundError",
    "ServiceException",
    "ValidationError",
]
