from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ApplePayStoreCredentials(BaseModel):
    """
    Apple Pay Store Connect API credentials.

    Used to authenticate with Apple's App Store Server API
    for purchase verification and subscription management.
    """

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        extra="forbid",
        frozen=True,
    )

    private_key: str = Field(
        ...,
        description="Content of .p8 private key file from Apple Pay Store Connect",
    )
    key_id: str = Field(
        ...,
        description="Key ID from Apple Pay Store Connect (10-character string)",
    )
    issuer_id: str = Field(
        ...,
        description="Issuer ID from Apple Pay Store Connect (UUID format)",
    )
    bundle_id: str = Field(
        ...,
        description="App bundle identifier from Apple Pay Store Connect",
    )


class FirebaseServiceAccount(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        extra="forbid",
    )

    type: str = "service_account"
    project_id: str
    private_key_id: str
    private_key: str
    private_key_path: Path | None = None
    client_email: str
    client_id: str
    auth_uri: str = "https://accounts.google.com/o/oauth2/auth"
    token_uri: str = "https://oauth2.googleapis.com/token"
    auth_provider_x509_cert_url: str = "https://www.googleapis.com/oauth2/v1/certs"
    client_x509_cert_url: str = "https://www.googleapis.com/robot/v1/metadata/x509/"
    universe_domain: str = "googleapis.com"

    @model_validator(mode="after")
    def validate_fields(self):
        self.client_x509_cert_url = self.client_x509_cert_url + self.client_email

        if self.private_key_path is not None and self.private_key_path.is_file():
            self.private_key = self.private_key_path.read_text()

        return self
