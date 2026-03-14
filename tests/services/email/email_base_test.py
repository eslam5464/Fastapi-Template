from pathlib import Path

import pytest

from app.services.email.base import BaseEmailService
from app.services.exceptions.email import EmailConfigurationError
from app.services.types.email import EmailSendPayload, EmailSendResult


class DummyEmailService(BaseEmailService):
    """Concrete base-service implementation used for base behavior tests."""

    def __init__(self, default_sender: str):
        super().__init__(default_sender=default_sender)
        self.last_payload: EmailSendPayload | None = None

    async def send(self, payload: EmailSendPayload) -> EmailSendResult:
        self.last_payload = payload
        return EmailSendResult(id="dummy_message_id", provider="resend")


class TestBaseEmailService:
    """Tests for template loading and helper behavior in the base class."""

    @pytest.mark.anyio
    async def test_send_welcome_uses_template_file(self, tmp_path: Path) -> None:
        """Welcome send should render template placeholders and pass payload to send."""
        html_dir: Path = tmp_path / "html"
        html_dir.mkdir(parents=True)
        (html_dir / "welcome.html").write_text("Hi {{first_name}}", encoding="utf-8")

        service = DummyEmailService(default_sender="noreply@example.com")
        service._html_templates_dir = html_dir

        result = await service.send_welcome(to="user@example.com", first_name="John")

        assert result.id == "dummy_message_id"
        assert service.last_payload is not None
        assert service.last_payload.to == ["user@example.com"]
        assert service.last_payload.subject == "Welcome to Evolve!"
        assert service.last_payload.html == "Hi John"

    def test_read_html_template_raises_for_missing_file(self, tmp_path: Path) -> None:
        """Missing template files should raise EmailConfigurationError."""
        service = DummyEmailService(default_sender="noreply@example.com")
        service._html_templates_dir = tmp_path

        with pytest.raises(EmailConfigurationError) as exc_info:
            service._read_html_template("missing.html")

        assert "Email template not found" in str(exc_info.value)

    def test_render_html_template_replaces_multiple_context_keys(self, tmp_path: Path) -> None:
        """Template renderer should replace all {{key}} placeholders."""
        html_dir: Path = tmp_path / "html"
        html_dir.mkdir(parents=True)
        (html_dir / "generic.html").write_text("Hello {{name}} from {{company}}", encoding="utf-8")

        service = DummyEmailService(default_sender="noreply@example.com")
        service._html_templates_dir = html_dir

        rendered = service._render_html_template(
            template_name="generic.html",
            context={"name": "Alice", "company": "Evolve"},
        )

        assert rendered == "Hello Alice from Evolve"
