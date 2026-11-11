# --- FEATURE[auth] START ---
from .auth import (
    JWTPayloadDict,
    LogoutRevokePayloadDict,
    TokenPairDict,
    TokenWithJtiDict,
)

# --- FEATURE[auth] END ---
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

__all__: list[str] = [
    # --- FEATURE[resend|brevo] START ---
    "EmailAttachment",
    "EmailProviderLiteral",
    "EmailSendPayload",
    "EmailSendResult",
    "EmailTag",
    "EmailTemplate",
    # --- FEATURE[resend|brevo] END ---
    # --- FEATURE[auth] START ---
    "JWTPayloadDict",
    "LogoutRevokePayloadDict",
    "TokenPairDict",
    "TokenWithJtiDict",
    # --- FEATURE[auth] END ---
]
