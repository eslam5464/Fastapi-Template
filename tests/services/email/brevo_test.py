from datetime import datetime
from unittest.mock import AsyncMock

import pytest

pytest.importorskip("brevo")

from app.services.email.brevo import BrevoEmailService
from app.services.exceptions.email import (
    EmailProviderError,
    EmailSendFailedError,
    EmailTemplateError,
)
from app.services.types.email import EmailAttachment, EmailSendPayload, EmailTemplate


class _ResponseObject:
    def __init__(self, message_id: str | None):
        self.message_id = message_id


class TestBrevoEmailService:
    """Tests for Brevo provider adapter behavior."""

    def test_parse_scheduled_at_accepts_z_suffix(self) -> None:
        """Z-suffixed timestamps should parse into datetime values."""
        result = BrevoEmailService._parse_scheduled_at("2026-01-01T00:00:00Z")

        assert isinstance(result, datetime)
        assert result.tzinfo is not None

    def test_parse_scheduled_at_rejects_invalid_format(self) -> None:
        """Invalid timestamps should raise provider error."""
        with pytest.raises(EmailProviderError):
            BrevoEmailService._parse_scheduled_at("invalid-date")

    def test_extract_message_id_from_mapping(self) -> None:
        """Message id should be extracted from mapping responses."""
        assert BrevoEmailService._extract_message_id({"message_id": "msg_1"}) == "msg_1"

    def test_extract_message_id_from_object(self) -> None:
        """Message id should be extracted from object responses."""
        assert BrevoEmailService._extract_message_id(_ResponseObject("msg_2")) == "msg_2"

    @pytest.mark.anyio
    async def test_send_success_returns_message_id(self) -> None:
        """Successful provider send should return normalized result."""
        service = BrevoEmailService(default_sender="noreply@example.com", api_key="brevo_test")
        service._client.transactional_emails.send_transac_email = AsyncMock(
            return_value={"message_id": "msg_123"}
        )

        payload = EmailSendPayload(
            sender="noreply@example.com",
            to=["user@example.com"],
            subject="subject",
            html="<p>ok</p>",
        )

        result = await service.send(payload)

        assert result.id == "msg_123"
        assert result.provider == "brevo"

    @pytest.mark.anyio
    async def test_send_raises_for_non_numeric_template_id(self) -> None:
        """Brevo template ids must be parseable as integers."""
        service = BrevoEmailService(default_sender="noreply@example.com", api_key="brevo_test")

        payload = EmailSendPayload(
            sender="noreply@example.com",
            to=["user@example.com"],
            subject="subject",
            template=EmailTemplate(id="not-numeric", variables={"name": "John"}),
        )

        with pytest.raises(EmailTemplateError):
            await service.send(payload)

    @pytest.mark.anyio
    async def test_send_wraps_provider_exception(self) -> None:
        """Provider exceptions should be wrapped as EmailSendFailedError."""
        service = BrevoEmailService(default_sender="noreply@example.com", api_key="brevo_test")
        service._client.transactional_emails.send_transac_email = AsyncMock(
            side_effect=RuntimeError("provider down")
        )

        payload = EmailSendPayload(
            sender="noreply@example.com",
            to=["user@example.com"],
            subject="subject",
            html="<p>ok</p>",
        )

        with pytest.raises(EmailSendFailedError) as exc_info:
            await service.send(payload)

        assert "Brevo send failed" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_send_raises_when_message_id_missing(self) -> None:
        """Missing message id in provider response should raise EmailProviderError."""
        service = BrevoEmailService(default_sender="noreply@example.com", api_key="brevo_test")
        service._client.transactional_emails.send_transac_email = AsyncMock(
            return_value={"ok": True}
        )

        payload = EmailSendPayload(
            sender="noreply@example.com",
            to=["user@example.com"],
            subject="subject",
            html="<p>ok</p>",
        )

        with pytest.raises(EmailProviderError):
            await service.send(payload)

    @pytest.mark.anyio
    async def test_send_maps_attachments_and_schedule(self) -> None:
        """Attachments and scheduled_at should be converted into Brevo request arguments."""
        service = BrevoEmailService(default_sender="noreply@example.com", api_key="brevo_test")
        mock_send = AsyncMock(return_value={"message_id": "msg_123"})
        service._client.transactional_emails.send_transac_email = mock_send

        payload = EmailSendPayload(
            sender="noreply@example.com",
            to=["user@example.com"],
            subject="subject",
            html="<p>ok</p>",
            scheduled_at="2026-01-01T00:00:00Z",
            attachments=[EmailAttachment(filename="a.txt", content="abc")],
        )

        await service.send(payload)

        assert mock_send.await_args is not None
        kwargs = mock_send.await_args.kwargs
        assert kwargs["scheduled_at"] is not None
        assert kwargs["attachment"] is not None
        assert len(kwargs["attachment"]) == 1
