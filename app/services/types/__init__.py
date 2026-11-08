from .auth import (
    JWTPayloadDict,
    LogoutRevokePayloadDict,
    TokenPairDict,
    TokenWithJtiDict,
)

# --- FEATURE[resend|brevo] START ---
from .email import (
    EmailAttachment,
    EmailProviderLiteral,
    EmailSendPayload,
    EmailSendResult,
    EmailTag,
    EmailTemplate,
)
# --- FEATURE[resend|brevo] END ---

__all__ = [
    # --- FEATURE[resend|brevo] START ---
    "EmailAttachment",
    "EmailProviderLiteral",
    "EmailSendPayload",
    "EmailSendResult",
    "EmailTag",
    "EmailTemplate",
    # --- FEATURE[resend|brevo] END ---
    "JWTPayloadDict",
    "LogoutRevokePayloadDict",
    "TokenPairDict",
    "TokenWithJtiDict",
]
