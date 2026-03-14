from abc import ABC, abstractmethod
from pathlib import Path

from app.services.exceptions.email import EmailConfigurationError
from app.services.types.email import EmailSendPayload, EmailSendResult


class BaseEmailService(ABC):
    """Abstract provider contract for sending transactional emails."""

    provider_name: str

    def __init__(self, default_sender: str):
        self.default_sender = default_sender
        self._html_templates_dir = Path(__file__).resolve().parent / "static"

    @abstractmethod
    async def send(self, payload: EmailSendPayload) -> EmailSendResult:
        """
        Send a provider-agnostic payload.

        Raises:
            EmailValidationError: If payload validation fails.
            EmailConfigurationError: If provider config is invalid.
            EmailSendFailedError: If provider send call fails.
            EmailProviderError: If provider returns an unexpected response payload.
        """

    async def send_welcome(self, to: str, first_name: str) -> EmailSendResult:
        """
        Send a default welcome email.

        Raises:
            EmailValidationError: If payload validation fails.
            EmailConfigurationError: If provider config is invalid.
            EmailSendFailedError: If provider send call fails.
            EmailProviderError: If provider returns an unexpected response payload.
        """
        html = self._build_welcome_html(first_name)
        return await self.send(
            EmailSendPayload(
                sender=self.default_sender,
                to=[to],
                subject="Welcome to Evolve!",
                html=html,
            )
        )

    def _read_html_template(self, template_name: str) -> str:
        """
        Read an HTML template from the email static template folder.

        Raises:
            EmailConfigurationError: If the template file cannot be found.
        """
        template_path = self._html_templates_dir / template_name
        if not template_path.is_file():
            raise EmailConfigurationError(f"Email template not found: {template_path}")

        return template_path.read_text(encoding="utf-8")

    def _render_html_template(self, template_name: str, context: dict[str, str]) -> str:
        """Render a template by replacing {{key}} placeholders from context."""
        rendered = self._read_html_template(template_name)
        for key, value in context.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)

        return rendered

    def _build_welcome_html(self, first_name: str) -> str:
        """Build the welcome email HTML from static template files."""
        return self._render_html_template(
            template_name="welcome.html",
            context={"first_name": first_name},
        )
