from pydantic import ConfigDict, EmailStr, Field

from app.schemas import BaseSchema


class FirebaseTokenData(BaseSchema):
    user_id: str
    email: str
    name: str | None
    issued: float
    expires: float
    issuer: str


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
