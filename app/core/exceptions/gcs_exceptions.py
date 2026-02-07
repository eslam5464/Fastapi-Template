from google.api_core.exceptions import NotFound

from app.core.exceptions.base import AppException


class GCSError(AppException):
    """
    Base exception for Google cloud service
    """

    def __init__(self, message, exception: Exception | None = None):
        super().__init__(message, exception)


class GCSBucketNotFoundError(GCSError):
    """
    Bucket does not exist in Google cloud service
    """

    def __init__(self, message, exception: NotFound | None = None):
        super().__init__(message, exception)


class GCSBucketNotSelectedError(GCSError):
    """
    Bucket is not selected
    """

    def __init__(self, message, exception: Exception | None = None):
        super().__init__(message, exception)
