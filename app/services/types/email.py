from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

EmailProviderLiteral = Literal["resend", "brevo"]


class EmailAttachment(BaseModel):
    """Attachment payload accepted by provider adapters."""

    model_config = ConfigDict(str_strip_whitespace=True)

    filename: str | None = None
    content: str | None = None
    path: str | None = None
    content_type: str | None = None
    content_id: str | None = None

    @model_validator(mode="after")
    def validate_source(self) -> "EmailAttachment":
        """Ensure an attachment has either inline content or a remote/local path."""
        if not self.content and not self.path:
            raise ValueError("Each attachment must include at least one of content or path")
        return self


class EmailTag(BaseModel):
    """Custom key/value tag attached to an email message."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=256)
    value: str = Field(min_length=1, max_length=256)


class EmailTemplate(BaseModel):
    """Template contract for provider-specific template sends."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(min_length=1)
    variables: dict[str, str | int] | None = None

    @field_validator("variables")
    @classmethod
    def validate_variables(cls, value: dict[str, str | int] | None) -> dict[str, str | int] | None:
        """Prevent empty template variables mappings when variables are provided."""
        if value is not None and not value:
            raise ValueError("template.variables cannot be an empty mapping")
        return value


class EmailSendPayload(BaseModel):
    """Provider-agnostic payload accepted by the email service layer."""

    model_config = ConfigDict(str_strip_whitespace=True)

    sender: str = Field(min_length=1)
    to: list[str]
    subject: str = Field(min_length=1)
    html: str | None = None
    text: str | None = None
    cc: list[str] | None = None
    bcc: list[str] | None = None
    reply_to: list[str] | None = None
    scheduled_at: str | None = None
    attachments: list[EmailAttachment] | None = None
    tags: list[EmailTag] | None = None
    headers: dict[str, str] | None = None
    topic_id: str | None = None
    template: EmailTemplate | None = None

    @field_validator("to", "cc", "bcc", "reply_to", mode="before")
    @classmethod
    def normalize_recipients(cls, value: str | list[str] | None) -> list[str] | None:
        """Accept both single-address strings and address lists."""
        if value is None:
            return None
        if isinstance(value, str):
            return [value]
        return value

    @field_validator("to", "cc", "bcc", "reply_to")
    @classmethod
    def validate_recipients(
        cls,
        value: list[str] | None,
        info: object,
    ) -> list[str] | None:
        """Ensure recipient fields are non-empty and contain non-blank addresses."""
        if value is None:
            return None

        if not value:
            field_name = info.field_name  # type: ignore[attr-defined]
            raise ValueError(f"{field_name} must contain at least one recipient")

        normalized = [item.strip() for item in value]
        if any(not item for item in normalized):
            field_name = info.field_name  # type: ignore[attr-defined]
            raise ValueError(f"{field_name} contains an empty email address")

        return normalized

    @model_validator(mode="after")
    def validate_content(self) -> "EmailSendPayload":
        """Enforce mutually exclusive template/content rules and minimum content."""
        has_html = bool(self.html)
        has_text = bool(self.text)
        has_template = self.template is not None

        if has_template and (has_html or has_text):
            raise ValueError("Cannot provide html/text alongside template")
        if not has_template and not has_html and not has_text:
            raise ValueError("One of html, text, or template is required")

        return self


class EmailSendResult(BaseModel):
    """Normalized send result returned by provider adapters."""

    id: str = Field(min_length=1)
    provider: EmailProviderLiteral
