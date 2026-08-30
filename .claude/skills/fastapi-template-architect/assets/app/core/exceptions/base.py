# --- SNAPSHOT NOTICE (fastapi-template-architect skill) ---
# Verbatim copy of app/core/exceptions/base.py from eslam5464/Fastapi-Template, taken 2026-08-30.
# The real repo is the source of truth; this is a fallback/reference copy
# for offline scaffolding and Extend/Audit-mode pattern-matching. It can drift
# from the live repo over time - prefer driving the real Copier template
# (see references/copier-template-mechanics.md) whenever that's available.
# --- END SNAPSHOT NOTICE ---

from typing import Any, Optional

from fastapi import HTTPException as FastAPIHTTPException


class AppException(Exception):
    """
    Base for all custom/domain exceptions.
    Services raise AppException subclasses; deps catch and translate to HTTP exceptions.
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
