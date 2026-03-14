import asyncio
from collections.abc import Mapping
from typing import cast

import resend
from loguru import logger

from app.core.config import settings
from app.services.email.base import BaseEmailService
from app.services.exceptions.email import (
    EmailProviderError,
    EmailSendFailedError,
)
from app.services.types.email import (
    EmailSendPayload,
    EmailSendResult,
)


class ResendEmailService(BaseEmailService):
    """Resend provider adapter for asynchronous email sending."""

    provider_name: str = "resend"

    def __init__(self, api_key: str, default_sender: str):
        """
        Initialize Resend adapter.
        """
        super().__init__(default_sender=default_sender)
        self._resend = resend
        self._resend.api_key = api_key or settings.resend_api_key.get_secret_value()

    @staticmethod
    def _build_provider_payload(
        payload: EmailSendPayload,
    ) -> dict[str, object]:
        """Map validated payload fields to the Resend API payload shape."""
        provider_payload: dict[str, object] = {
            "from": payload.sender,
            "to": payload.to,
            "subject": payload.subject,
        }

        if payload.html is not None:
            provider_payload["html"] = payload.html
        if payload.text is not None:
            provider_payload["text"] = payload.text
        if payload.cc is not None:
            provider_payload["cc"] = payload.cc
        if payload.bcc is not None:
            provider_payload["bcc"] = payload.bcc
        if payload.reply_to is not None:
            provider_payload["reply_to"] = payload.reply_to
        if payload.scheduled_at is not None:
            provider_payload["scheduledAt"] = payload.scheduled_at
        if payload.attachments is not None:
            provider_payload["attachments"] = [
                attachment.model_dump(exclude_none=True) for attachment in payload.attachments
            ]
        if payload.tags is not None:
            provider_payload["tags"] = [tag.model_dump(exclude_none=True) for tag in payload.tags]
        if payload.headers is not None:
            provider_payload["headers"] = payload.headers
        if payload.topic_id is not None:
            provider_payload["topicId"] = payload.topic_id
        if payload.template is not None:
            provider_payload["template"] = payload.template.model_dump(exclude_none=True)

        return provider_payload

    async def send(self, payload: EmailSendPayload) -> EmailSendResult:
        """
        Send an email through the Resend Python SDK.

        The official SDK is synchronous, so this call is wrapped with ``asyncio.to_thread``.

        Raises:
                EmailValidationError: If payload validation fails.
                EmailSendFailedError: If the provider call fails.
                EmailProviderError: If the provider response is missing a message id.
        """
        provider_payload = self._build_provider_payload(payload)

        logger.debug(
            "Sending email via resend | to={} | subject={}",
            payload.to,
            payload.subject,
        )

        try:
            response = await asyncio.to_thread(
                self._resend.Emails.send,
                cast("resend.Emails.SendParams", provider_payload),
            )
        except Exception as exc:
            logger.exception("Resend email send failed")
            raise EmailSendFailedError(f"Resend send failed: {exc}") from exc

        if not isinstance(response, Mapping):
            raise EmailProviderError("Resend response is not a mapping")

        message_id = response.get("id")
        if not isinstance(message_id, str) or not message_id:
            raise EmailProviderError("Resend response does not include a valid 'id'")

        return EmailSendResult(id=message_id, provider="resend")
