from pathlib import Path

from pydantic import ConfigDict, EmailStr, Field, model_validator

from app.schemas import BaseSchema


class FirebaseTokenData(BaseSchema):
    user_id: str
    email: str
    name: str | None
    issued: float
    expires: float
    issuer: str


class FirebaseServiceAccount(BaseSchema):
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


class FirebaseSignInResponse(BaseSchema):
    id_token: str
    decoded_token: FirebaseTokenData | None
    email: str
    refresh_token: str
    expires_in: int
    local_id: str
    registered: bool


class FirebaseSignUpResponse(BaseSchema):
    id_token: str
    decoded_token: FirebaseTokenData | None
    email: str
    refresh_token: str
    expires_in: int
    local_id: str


class DecodedFirebaseTokenResponse(BaseSchema):
    iss: str = Field(description="Issuer of the token")
    aud: str = Field(description="Audience of the token")
    auth_time: int = Field(description="Authentication time")
    user_id: str = Field(description="User ID")
    sub: str = Field(description="Subject of the token")
    iat: int = Field(description="Issued at time")
    exp: int = Field(description="Expiration time")
    email: EmailStr = Field(description="User email")
    email_verified: bool = Field(description="Email verification status")
    firebase: dict = Field(description="Firebase specific claims")
    uid: str = Field(description="User ID")

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        extra="allow",
    )
