from pydantic import Field

from app.schemas import BaseSchema


class ApplePayStoreCredentials(BaseSchema):
    """
    Apple Pay Store Connect API credentials.

    Used to authenticate with Apple's App Store Server API
    for purchase verification and subscription management.
    """

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

    class Config:
        frozen = True
