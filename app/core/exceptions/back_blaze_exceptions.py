from b2sdk.v2.exception import NonExistentBucket

from app.core.exceptions.base import CustomException


class BlackBlazeError(CustomException):
    """
    Base exception for black blaze b2
    """

    def __init__(self, message, exception: Exception | None = None):
        super().__init__(message, exception)


class B2BucketOperationError(BlackBlazeError):
    """
    Bucket operation error for black blaze b2
    """

    def __init__(self, message, exception: Exception | None = None):
        super().__init__(message, exception)


class B2BucketNotFoundError(BlackBlazeError):
    """
    Bucket does not exist in black blaze
    """

    def __init__(
        self,
        message,
        exception: NonExistentBucket | None = None,
    ):
        super().__init__(message, exception)


class B2BucketNotSelectedError(BlackBlazeError):
    """
    Bucket is not selected
    """

    def __init__(self, message, exception: Exception | None = None):
        super().__init__(message, exception)


class B2AuthorizationError(BlackBlazeError):
    """
    Authorization error for black blaze b2
    """

    def __init__(self, message, exception: Exception | None = None):
        super().__init__(message, exception)


class B2FileOperationError(BlackBlazeError):
    """
    File operation error for black blaze b2
    """

    def __init__(self, message, exception: Exception | None = None):
        super().__init__(message, exception)
