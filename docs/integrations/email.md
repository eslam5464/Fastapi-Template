# Email

`app/services/email/` holds a provider-agnostic email layer:

- `base.py`: `BaseEmailService`, the contract every provider implements (`send()`), plus
  `send_welcome()` built on the HTML templates in `static/`
- `app/services/types/email.py`: the Pydantic payload and result types
  (`EmailSendPayload`, `EmailSendResult`, `EmailAttachment`, `EmailTag`, `EmailTemplate`)
- `app/services/exceptions/email.py`: `EmailValidationError`, `EmailConfigurationError`,
  `EmailSendFailedError`, `EmailProviderError`, `EmailTemplateError`

Each provider is its own choice when the project is generated
(`--data services=custom --data include_<provider>=true`, or "yes" to the matching
question). The shared layer is included when at least one provider is.

## Providers

<!-- --- FEATURE[resend] START --- -->
### Resend

`app/services/email/resend.py` (`ResendEmailService`), using the `resend` package.
Set `RESEND_API_KEY` (create a key in the Resend dashboard and verify your sending
domain there).

```python
from app.core.config import settings
from app.services.email.resend import ResendEmailService

email_service = ResendEmailService(
    api_key=settings.resend_api_key.get_secret_value(),
    default_sender="App <noreply@example.com>",
)
```

<!-- --- FEATURE[resend] END --- -->
<!-- --- FEATURE[brevo] START --- -->
### Brevo

`app/services/email/brevo.py` (`BrevoEmailService`), using the `brevo-python` package.
Set `BREVO_API_KEY` (create a key under SMTP & API in Brevo and verify your sender).

```python
from app.services.email.brevo import BrevoEmailService

email_service = BrevoEmailService(default_sender="App <noreply@example.com>")  # api_key defaults to BREVO_API_KEY
```

<!-- --- FEATURE[brevo] END --- -->
## Sending

Every provider takes the same payload, so switching providers does not change calling code.

```python
from app.services.types.email import EmailSendPayload

result = await email_service.send(
    EmailSendPayload(
        sender="App <noreply@example.com>",
        to="user@example.com",  # a single address or a list
        subject="Your receipt",
        html="<p>Thanks for your order.</p>",
        text="Thanks for your order.",
    )
)
print(result.provider, result.id)

await email_service.send_welcome(to="user@example.com", first_name="Sam")
```

Payload validation errors raise `EmailValidationError`; provider failures raise
`EmailSendFailedError` or `EmailProviderError`.

## Production

1. Create API keys only for the provider(s) you use, scoped to sending.
2. Keep them in your secret manager and inject them at runtime (never in the image or the repository).
3. Verify the sending domain (SPF, DKIM) with the provider before going live.
