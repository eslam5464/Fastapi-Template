from typing import Any, Optional

from fastapi import HTTPException as FastAPIHTTPException


class CustomException(Exception):
    """
    Base for all custom exceptions
    """

    def __init__(self, message, exception: Exception | None = None):
        super().__init__(message)
        self.message = message
        self.exception = exception

    def __str__(self):
        if self.exception:
            return f"{self.message}\nException: {self.exception}"

        return self.message


class HTTPException(FastAPIHTTPException):
    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        """
        Initializes the HTTPException with the provided status code, detail, and headers.
        :param status_code: The HTTP status code for the exception.
        :param detail: Optional message or data providing details about the exception.
        :param headers: Optional headers to include in the HTTP response.
        """
        super().__init__(status_code=status_code, detail=detail, headers=headers)
