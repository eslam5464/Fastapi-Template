from unittest.mock import AsyncMock, patch

import pytest

resend = pytest.importorskip("resend")

from app.services.email.resend import ResendEmailService
from app.services.exceptions.email import EmailProviderError, EmailSendFailedError
from app.services.types.email import EmailAttachment, EmailSendPayload, EmailTag, EmailTemplate


class TestResendEmailService:
    """Tests for Resend provider adapter behavior."""

    def test_build_provider_payload_maps_optional_fields(self) -> None:
        """Payload mapping should include optional fields in Resend shape."""
        payload = EmailSendPayload(
            sender="noreply@example.com",
            to=["user@example.com"],
            subject="subject",
            html="<p>html</p>",
            text="plain",
            cc=["cc@example.com"],
            bcc=["bcc@example.com"],
            reply_to=["reply@example.com"],
            scheduled_at="2026-01-01T00:00:00Z",
            attachments=[EmailAttachment(filename="a.txt", content="abc")],
            tags=[EmailTag(name="env", value="test")],
            headers={"X-Test": "1"},
            topic_id="topic_1",
        )

        mapped = ResendEmailService._build_provider_payload(payload)

        assert mapped["from"] == "noreply@example.com"
        assert mapped["to"] == ["user@example.com"]
        assert mapped["subject"] == "subject"
        assert mapped["scheduledAt"] == "2026-01-01T00:00:00Z"
        assert isinstance(mapped["attachments"], list)
        assert isinstance(mapped["tags"], list)

        template_payload = EmailSendPayload(
            sender="noreply@example.com",
            to=["user@example.com"],
            subject="subject",
            template=EmailTemplate(id="tpl_1", variables={"name": "John"}),
        )
        template_mapped = ResendEmailService._build_provider_payload(template_payload)

        assert isinstance(template_mapped["template"], dict)

    @pytest.mark.anyio
    async def test_send_success_returns_message_id(self) -> None:
        """Successful provider response should return normalized result."""
        service = ResendEmailService(api_key="re_test", default_sender="noreply@example.com")
        payload = EmailSendPayload(
            sender="noreply@example.com",
            to=["user@example.com"],
            subject="subject",
            html="<p>ok</p>",
        )

        with patch(
            "app.services.email.resend.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_thread:
            mock_thread.return_value = {"id": "email_123"}
            result = await service.send(payload)

        assert result.id == "email_123"
        assert result.provider == "resend"

    @pytest.mark.anyio
    async def test_send_raises_on_non_mapping_response(self) -> None:
        """Non-mapping provider responses should raise EmailProviderError."""
        service = ResendEmailService(api_key="re_test", default_sender="noreply@example.com")
        payload = EmailSendPayload(
            sender="noreply@example.com",
            to=["user@example.com"],
            subject="subject",
            html="<p>ok</p>",
        )

        with patch(
            "app.services.email.resend.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_thread:
            mock_thread.return_value = "not-a-dict"
            with pytest.raises(EmailProviderError):
                await service.send(payload)

    @pytest.mark.anyio
    async def test_send_raises_on_missing_id(self) -> None:
        """Provider responses without valid id should raise EmailProviderError."""
        service = ResendEmailService(api_key="re_test", default_sender="noreply@example.com")
        payload = EmailSendPayload(
            sender="noreply@example.com",
            to=["user@example.com"],
            subject="subject",
            html="<p>ok</p>",
        )

        with patch(
            "app.services.email.resend.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_thread:
            mock_thread.return_value = {"status": "ok"}
            with pytest.raises(EmailProviderError):
                await service.send(payload)

    @pytest.mark.anyio
    async def test_send_wraps_provider_exception(self) -> None:
        """Provider exceptions should be wrapped as EmailSendFailedError."""
        service = ResendEmailService(api_key="re_test", default_sender="noreply@example.com")
        payload = EmailSendPayload(
            sender="noreply@example.com",
            to=["user@example.com"],
            subject="subject",
            html="<p>ok</p>",
        )

        with patch(
            "app.services.email.resend.asyncio.to_thread", new_callable=AsyncMock
        ) as mock_thread:
            mock_thread.side_effect = RuntimeError("provider down")
            with pytest.raises(EmailSendFailedError) as exc_info:
                await service.send(payload)

        assert "Resend send failed" in str(exc_info.value)
