import pytest
from pydantic import ValidationError

from app.services.types.email import (
    EmailAttachment,
    EmailSendPayload,
    EmailSendResult,
    EmailTag,
    EmailTemplate,
)


class TestEmailTypesValidation:
    """Validation tests for Pydantic email payload models."""

    def test_attachment_requires_content_or_path(self) -> None:
        """Attachment without content/path should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            EmailAttachment(filename="file.txt")

        assert "content or path" in str(exc_info.value)

    def test_template_rejects_empty_variables(self) -> None:
        """Template variables cannot be an empty mapping."""
        with pytest.raises(ValidationError) as exc_info:
            EmailTemplate(id="tpl_1", variables={})

        assert "empty mapping" in str(exc_info.value)

    def test_payload_normalizes_single_recipient_to_list(self) -> None:
        """Single recipient strings should normalize to lists."""
        payload = EmailSendPayload.model_validate(
            {
                "sender": "noreply@example.com",
                "to": "user@example.com",
                "subject": "hello",
                "html": "<p>hello</p>",
            }
        )

        assert payload.to == ["user@example.com"]

    def test_payload_rejects_blank_recipient(self) -> None:
        """Recipient lists with blank entries should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            EmailSendPayload(
                sender="noreply@example.com",
                to=["user@example.com", "  "],
                subject="hello",
                html="<p>hello</p>",
            )

        assert "contains an empty email address" in str(exc_info.value)

    def test_payload_requires_content_or_template(self) -> None:
        """At least one of html/text/template is required."""
        with pytest.raises(ValidationError) as exc_info:
            EmailSendPayload(
                sender="noreply@example.com",
                to=["user@example.com"],
                subject="hello",
            )

        assert "One of html, text, or template is required" in str(exc_info.value)

    def test_payload_rejects_template_with_html_or_text(self) -> None:
        """Template cannot be sent with html/text content simultaneously."""
        with pytest.raises(ValidationError) as exc_info:
            EmailSendPayload(
                sender="noreply@example.com",
                to=["user@example.com"],
                subject="hello",
                html="<p>hello</p>",
                template=EmailTemplate(id="tpl_1", variables={"name": "John"}),
            )

        assert "Cannot provide html/text alongside template" in str(exc_info.value)

    def test_payload_accepts_template_only(self) -> None:
        """Template-only payload should pass validation."""
        payload = EmailSendPayload(
            sender="noreply@example.com",
            to=["user@example.com"],
            subject="hello",
            template=EmailTemplate(id="1", variables={"name": "John"}),
        )

        assert payload.template is not None
        assert payload.template.id == "1"

    def test_payload_strips_whitespace(self) -> None:
        """String fields should be stripped by model config."""
        payload = EmailSendPayload(
            sender="  noreply@example.com  ",
            to=["  user@example.com  "],
            subject="  hello  ",
            text="  body  ",
        )

        assert payload.sender == "noreply@example.com"
        assert payload.to == ["user@example.com"]
        assert payload.subject == "hello"
        assert payload.text == "body"

    def test_result_provider_literal_validation(self) -> None:
        """Result provider must match supported literals."""
        with pytest.raises(ValidationError):
            EmailSendResult(id="msg_1", provider="unknown")  # type: ignore[arg-type]

    def test_tag_length_validation(self) -> None:
        """Tags should enforce max length constraints."""
        oversized_name: str = "x" * 257
        with pytest.raises(ValidationError):
            EmailTag(name=oversized_name, value="ok")
