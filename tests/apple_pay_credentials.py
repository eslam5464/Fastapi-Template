import os
from pathlib import Path


def ensure_apple_pay_test_credentials() -> None:
    """
    Generate throwaway Apple Pay test credentials before any `app.*` module is imported.

    `app/services/payments/apple_pay.py` builds a module-level `ApplePay()` singleton at
    import time, which eagerly PEM-parses the private key (and, for webhook/receipt
    verification, reads the root certificate file's bytes). Real Apple API calls are
    always mocked in tests, but these files still need to exist and be syntactically
    valid just to *import* the module — `.env.example`'s Apple Pay values are
    intentionally empty/placeholder (real credentials, not runnable as-is).

    Generating them here (module scope, before the `app.*` imports below) rather than in
    a fixture means they exist before pytest even starts collecting test modules — a
    fixture would run too late, since the crash happens at import time. This runs
    identically locally and in CI/CD; no separate CI-only credential-generation step
    needed. The env vars set here take precedence over whatever `.env` has, since
    pydantic-settings resolves environment variables before dotenv file values.
    """
    creds_dir = Path(__file__).resolve().parent.parent / ".apple_pay_test_credentials"
    creds_dir.mkdir(exist_ok=True)

    key_path = creds_dir / "test_key.p8"
    if not key_path.exists():
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec

        key = ec.generate_private_key(ec.SECP256R1())
        key_path.write_bytes(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    cert_path = creds_dir / "test_root_ca.cer"
    if not cert_path.exists():
        cert_path.write_text("dummy cert content for tests\n")

    os.environ["APPLE_PAY_STORE_PRIVATE_KEY_PATH"] = str(key_path)
    os.environ["APPLE_PAY_STORE_ROOT_CERTIFICATE_PATH"] = str(cert_path)
