from typing import Any, Optional

from starlette import status

from app.core.exceptions.base import HTTPException


class BadRequestException(HTTPException):
    def __init__(
        self,
        detail: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        """
        The server cannot or will not process the request due to an apparent
        client error (e.g., malformed request syntax, size too large,
        invalid request message framing, or deceptive request routing).
        :param detail: Optional detailed message or data about the exception.
        :param headers: Optional headers to include in the response.
        """
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            headers=headers,
        )


class ForbiddenException(HTTPException):
    def __init__(
        self,
        detail: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        """
        The request contained valid data and was understood by the server, but the
        server is refusing action. This may be due to the user not having the
        necessary permissions for a resource or needing an account of some sort,
        or attempting a prohibited action (e.g. creating a duplicate record where
        only one is allowed). This code is also typically used if the request
        provided authentication by answering the WWW-Authenticate header field
        challenge, but the server did not accept that authentication.
        The request should not be repeated.
        :param detail: Optional detailed message or data about the exception.
        :param headers: Optional headers to include in the response.
        """
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            headers=headers,
        )


class InternalServerErrorException(HTTPException):
    def __init__(
        self,
        detail: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        """
        A generic error message, given when an unexpected condition was
        encountered and no more specific message is suitable.
        :param detail: Optional detailed message or data about the exception.
        :param headers: Optional headers to include in the response.
        """
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            headers=headers,
        )


class NotFoundException(HTTPException):
    def __init__(
        self,
        detail: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        """
        The requested resource could not be found but may be available in the
        future. Subsequent requests by the client are permissible.
        :param detail: Optional detailed message or data about the exception.
        :param headers: Optional headers to include in the response.
        """
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            headers=headers,
        )


class NotImplementedException(HTTPException):
    def __init__(
        self,
        detail: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        """
        The server either does not recognize the request method,
        or it lacks the ability to fulfil the request.
        Usually this implies future availability
        (e.g., a new feature of a web-service API).
        :param detail: Optional detailed message or data about the exception.
        :param headers: Optional headers to include in the response.
        """
        super().__init__(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=detail,
            headers=headers,
        )


class ServiceUnavailableException(HTTPException):
    def __init__(
        self,
        detail: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        """
        The server cannot handle the request (because it is overloaded or
        down for maintenance). Generally, this is a temporary state.
        :param detail: Optional detailed message or data about the exception.
        :param headers: Optional headers to include in the response.
        """

        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            headers=headers,
        )


class TooManyRequestsException(HTTPException):
    def __init__(
        self,
        detail: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        """
        The user has sent too many requests in a given amount of time.
        :param detail: Optional detailed message or data about the exception.
        :param headers: Optional headers to include in the response.
        """

        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers,
        )


class UnauthorizedException(HTTPException):
    def __init__(
        self,
        detail: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        """
        Similar to 403 Forbidden, but specifically for use when authentication is
        required and has failed or has not yet been provided. The response must
        include a WWW-Authenticate header field containing a challenge applicable
        to the requested resource. See Basic access authentication and Digest access
        authentication. 401 semantically means "unauthorised", the user does not
        have valid authentication credentials for the target resource.
        Some sites incorrectly issue HTTP 401 when an IP address is banned from the
        website (usually the website domain) and that specific address is refused
        permission to access a website.
        :param detail: Optional detailed message or data about the exception.
        :param headers: Optional headers to include in the response.
        """
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers=headers,
        )


class ConflictException(HTTPException):
    def __init__(
        self,
        detail: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        """
        Indicates that the request could not be processed because of conflict in the
        current state of the resource. This code is typically used in response to a PUT
        request that would result in a conflict with the current state of the resource.
        :param detail: Optional detailed message or data about the exception.
        :param headers: Optional headers to include in the response.
        """
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            headers=headers,
        )


class ContentTooLargeException(HTTPException):
    def __init__(
        self,
        detail: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        """
        The request is larger than the server is willing or able to process.
        :param detail: Optional detailed message or data about the exception.
        :param headers: Optional headers to include in the response.
        """
        super().__init__(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=detail,
            headers=headers,
        )
