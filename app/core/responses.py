from pydantic import BaseModel


class BadRequestResponse(BaseModel):
    detail: str = "Bad request"


class InternalServerErrorResponse(BaseModel):
    detail: str = "Response details"


class ForbiddenResponse(BaseModel):
    detail: str = "Forbidden"


class NotFoundResponse(BaseModel):
    detail: str = "Not found"


class NotImplementedResponse(BaseModel):
    detail: str = "Not implemented"


class ServiceUnavailableResponse(BaseModel):
    detail: str = "Service unavailable"


class TooManyRequestsResponse(BaseModel):
    detail: str = "Too many requests"


class UnauthorizedResponse(BaseModel):
    detail: str = "Unauthorized"


class ConflictResponse(BaseModel):
    detail: str = "Conflict"


class ContentTooLargeResponse(BaseModel):
    detail: str = "Content too large"
