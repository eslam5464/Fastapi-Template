from starlette import status

from app.core.exceptions.http_exceptions import (
    BadRequestException,
    ConflictException,
    ContentTooLargeException,
    ForbiddenException,
    InternalServerErrorException,
    NotFoundException,
    NotImplementedException,
    ServiceUnavailableException,
    TooManyRequestsException,
    UnauthorizedException,
)


class TestHTTPExceptions:
    """Test HTTP exception classes."""

    def test_not_implemented_exception(self):
        """Test NotImplementedException instantiation and properties."""
        detail = "This feature is not yet implemented"
        exception = NotImplementedException(detail=detail)

        assert exception.status_code == status.HTTP_501_NOT_IMPLEMENTED
        assert exception.detail == detail
        assert exception.headers is None

    def test_not_implemented_exception_with_headers(self):
        """Test NotImplementedException with custom headers."""
        detail = "Not available"
        headers = {"X-Custom-Header": "value"}
        exception = NotImplementedException(detail=detail, headers=headers)

        assert exception.status_code == status.HTTP_501_NOT_IMPLEMENTED
        assert exception.detail == detail
        assert exception.headers == headers

    def test_service_unavailable_exception(self):
        """Test ServiceUnavailableException instantiation and properties."""
        detail = "Service is temporarily unavailable"
        exception = ServiceUnavailableException(detail=detail)

        assert exception.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert exception.detail == detail
        assert exception.headers is None

    def test_service_unavailable_exception_with_headers(self):
        """Test ServiceUnavailableException with custom headers."""
        detail = "Under maintenance"
        headers = {"Retry-After": "3600"}
        exception = ServiceUnavailableException(detail=detail, headers=headers)

        assert exception.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert exception.detail == detail
        assert exception.headers == headers

    def test_conflict_exception(self):
        """Test ConflictException instantiation and properties."""
        detail = "Resource already exists"
        exception = ConflictException(detail=detail)

        assert exception.status_code == status.HTTP_409_CONFLICT
        assert exception.detail == detail
        assert exception.headers is None

    def test_conflict_exception_with_headers(self):
        """Test ConflictException with custom headers."""
        detail = "Duplicate resource"
        headers = {"X-Conflict-ID": "12345"}
        exception = ConflictException(detail=detail, headers=headers)

        assert exception.status_code == status.HTTP_409_CONFLICT
        assert exception.detail == detail
        assert exception.headers == headers

    def test_content_too_large_exception(self):
        """Test ContentTooLargeException instantiation and properties."""
        detail = "Request payload is too large"
        exception = ContentTooLargeException(detail=detail)

        assert exception.status_code == status.HTTP_413_CONTENT_TOO_LARGE
        assert exception.detail == detail
        assert exception.headers is None

    def test_content_too_large_exception_with_headers(self):
        """Test ContentTooLargeException with custom headers."""
        detail = "File size exceeds limit"
        headers = {"X-Max-Size": "10MB"}
        exception = ContentTooLargeException(detail=detail, headers=headers)

        assert exception.status_code == status.HTTP_413_CONTENT_TOO_LARGE
        assert exception.detail == detail
        assert exception.headers == headers

    def test_exception_with_dict_detail(self):
        """Test exceptions with complex dict detail."""
        detail = {
            "message": "Validation failed",
            "errors": ["field1 is required", "field2 is invalid"],
        }
        exception = BadRequestException(detail=detail)

        assert exception.status_code == status.HTTP_400_BAD_REQUEST
        assert exception.detail == detail
        assert isinstance(exception.detail, dict)

    def test_exception_with_list_detail(self):
        """Test exceptions with list detail."""
        detail = ["Error 1", "Error 2", "Error 3"]
        exception = BadRequestException(detail=detail)

        assert exception.status_code == status.HTTP_400_BAD_REQUEST
        assert exception.detail == detail
        assert isinstance(exception.detail, list)

    def test_exception_with_none_detail(self):
        """Test exceptions with None detail."""
        exception = NotFoundException(detail=None)

        assert exception.status_code == status.HTTP_404_NOT_FOUND
        # FastAPI HTTPException provides default status text when detail=None
        assert exception.detail == "Not Found"

    def test_exception_with_multiple_headers(self):
        """Test exceptions with multiple custom headers."""
        headers = {
            "X-Request-ID": "abc123",
            "X-Error-Code": "E1001",
            "X-Timestamp": "2024-01-01T00:00:00Z",
        }
        exception = InternalServerErrorException(detail="Server error", headers=headers)

        assert exception.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exception.headers == headers
        assert exception.headers is not None
        assert len(exception.headers) == 3

    def test_bad_request_exception_default(self):
        """Test BadRequestException with defaults."""
        exception = BadRequestException()

        assert exception.status_code == status.HTTP_400_BAD_REQUEST
        assert exception.detail == "Bad Request"
        assert exception.headers is None

    def test_forbidden_exception_default(self):
        """Test ForbiddenException with defaults."""
        exception = ForbiddenException()

        assert exception.status_code == status.HTTP_403_FORBIDDEN
        assert exception.detail == "Forbidden"
        assert exception.headers is None

    def test_internal_server_error_exception_default(self):
        """Test InternalServerErrorException with defaults."""
        exception = InternalServerErrorException()

        assert exception.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exception.detail == "Internal Server Error"
        assert exception.headers is None

    def test_not_found_exception_default(self):
        """Test NotFoundException with defaults."""
        exception = NotFoundException()

        assert exception.status_code == status.HTTP_404_NOT_FOUND
        assert exception.detail == "Not Found"
        assert exception.headers is None

    def test_not_implemented_exception_default(self):
        """Test NotImplementedException with defaults."""
        exception = NotImplementedException()

        assert exception.status_code == status.HTTP_501_NOT_IMPLEMENTED
        assert exception.detail == "Not Implemented"
        assert exception.headers is None

    def test_service_unavailable_exception_default(self):
        """Test ServiceUnavailableException with defaults."""
        exception = ServiceUnavailableException()

        assert exception.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert exception.detail == "Service Unavailable"
        assert exception.headers is None

    def test_too_many_requests_exception_default(self):
        """Test TooManyRequestsException with defaults."""
        exception = TooManyRequestsException()

        assert exception.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert exception.detail == "Too Many Requests"
        assert exception.headers is None

    def test_unauthorized_exception_default(self):
        """Test UnauthorizedException with defaults."""
        exception = UnauthorizedException()

        assert exception.status_code == status.HTTP_401_UNAUTHORIZED
        assert exception.detail == "Unauthorized"
        assert exception.headers is None

    def test_conflict_exception_default(self):
        """Test ConflictException with defaults."""
        exception = ConflictException()

        assert exception.status_code == status.HTTP_409_CONFLICT
        assert exception.detail == "Conflict"
        assert exception.headers is None

    def test_content_too_large_exception_default(self):
        """Test ContentTooLargeException with defaults."""
        exception = ContentTooLargeException()

        assert exception.status_code == status.HTTP_413_CONTENT_TOO_LARGE
        assert exception.detail == "Content Too Large"
        assert exception.headers is None

    def test_exception_with_numeric_detail(self):
        """Test exceptions with numeric detail."""
        exception = BadRequestException(detail=404)

        assert exception.detail == 404

    def test_exception_with_boolean_detail(self):
        """Test exceptions with boolean detail."""
        exception = ConflictException(detail=True)

        assert exception.detail is True

    def test_exception_header_override(self):
        """Test that custom headers are preserved."""
        original_headers = {"X-Custom": "original"}
        exception = UnauthorizedException(detail="Auth failed", headers=original_headers)

        # Headers should be the same object
        assert exception.headers is original_headers
        assert exception.headers is not None
        assert exception.headers["X-Custom"] == "original"
