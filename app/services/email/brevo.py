from collections.abc import Mapping
from datetime import datetime

from brevo import AsyncBrevo
from brevo.transactional_emails import (
    SendTransacEmailRequestAttachmentItem,
    SendTransacEmailRequestBccItem,
    SendTransacEmailRequestCcItem,
    SendTransacEmailRequestReplyTo,
    SendTransacEmailRequestSender,
    SendTransacEmailRequestToItem,
)
from loguru import logger

from app.core.config import settings
from app.services.email.base import BaseEmailService
from app.services.exceptions.email import (
    EmailProviderError,
    EmailSendFailedError,
    EmailTemplateError,
)
from app.services.types.email import (
    EmailSendPayload,
    EmailSendResult,
)


class BrevoEmailService(BaseEmailService):
    """Brevo provider adapter using the official native async SDK client."""

    provider_name: str = "brevo"

    def __init__(self, default_sender: str, api_key: str | None = None):
        """
        Initialize Brevo adapter.
        """
        super().__init__(default_sender=default_sender)

        if not api_key:
            api_key = settings.brevo_api_key.get_secret_value()

        self._client = AsyncBrevo(api_key=api_key)

    @staticmethod
    def _parse_scheduled_at(value: str) -> datetime:
        """
        Parse ISO datetime for Brevo scheduled sends.

        Raises:
                EmailValidationError: If the datetime format is not valid ISO-8601.
        """
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise EmailProviderError(
                "scheduled_at must be an ISO-8601 datetime string for Brevo"
            ) from exc

    @staticmethod
    def _extract_message_id(response: object) -> str | None:
        """Extract provider message id from Brevo SDK response payload."""
        if isinstance(response, Mapping):
            raw_message_id = response.get("message_id")
            if isinstance(raw_message_id, str) and raw_message_id:
                return raw_message_id
            return None

        message_id = getattr(response, "message_id", None)
        if isinstance(message_id, str) and message_id:
            return message_id

        return None

    async def send(self, payload: EmailSendPayload) -> EmailSendResult:
        """
        Send an email through the Brevo Python SDK async client.

        Raises:
                EmailValidationError: If payload validation fails.
                EmailSendFailedError: If the provider call fails.
                EmailProviderError: If the provider response is missing a message id.
        """
        logger.debug(
            "Sending email via brevo | to={} | subject={}",
            payload.to,
            payload.subject,
        )

        sender = SendTransacEmailRequestSender(email=payload.sender)
        to_items = [SendTransacEmailRequestToItem(email=recipient) for recipient in payload.to]

        cc_items = None
        if payload.cc is not None:
            cc_items = [SendTransacEmailRequestCcItem(email=recipient) for recipient in payload.cc]

        bcc_items = None
        if payload.bcc is not None:
            bcc_items = [
                SendTransacEmailRequestBccItem(email=recipient) for recipient in payload.bcc
            ]

        reply_to = None
        if payload.reply_to:
            reply_to = SendTransacEmailRequestReplyTo(email=payload.reply_to[0])

        attachment_items = None
        if payload.attachments is not None:
            attachment_items = [
                SendTransacEmailRequestAttachmentItem(
                    name=item.filename,
                    content=item.content,
                    url=item.path,
                )
                for item in payload.attachments
            ]

        template_id = None
        params = None
        if payload.template is not None:
            raw_template_id = payload.template.id
            try:
                template_id = int(raw_template_id)
            except ValueError as exc:
                raise EmailTemplateError(
                    "Brevo template.id must be numeric (stringified integer)"
                ) from exc

            params = payload.template.variables

        scheduled_at = None
        if payload.scheduled_at is not None:
            scheduled_at = self._parse_scheduled_at(payload.scheduled_at)

        try:
            response = await self._client.transactional_emails.send_transac_email(
                sender=sender,
                to=to_items,
                subject=payload.subject,
                html_content=payload.html,
                text_content=payload.text,
                cc=cc_items,
                bcc=bcc_items,
                reply_to=reply_to,
                headers=payload.headers,
                scheduled_at=scheduled_at,
                template_id=template_id,
                params=params,
                attachment=attachment_items,
            )
        except Exception as exc:
            logger.exception("Brevo email send failed")
            raise EmailSendFailedError(f"Brevo send failed: {exc}") from exc

        message_id = self._extract_message_id(response)
        if message_id is None:
            raise EmailProviderError("Brevo response does not include a valid 'message_id'")

        return EmailSendResult(id=message_id, provider="brevo")
