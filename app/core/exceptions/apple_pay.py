from app.core.exceptions.base import AppException


class AppStoreException(AppException):
    """
    Exception related to App Store operations
    """

    def __init__(self, message, exception: Exception | None = None):
        super().__init__(message, exception)


class AppStoreClientNotInitializedException(AppStoreException):
    """
    Exception raised when the App Store client is not initialized
    """

    def __init__(
        self,
        message="App Store client not initialized",
        exception: Exception | None = None,
    ):
        super().__init__(message, exception)


class AppStoreNotFoundException(AppStoreException):
    """
    Exception raised when the App Store resource is not found
    """

    def __init__(
        self,
        message="App Store resource not found",
        exception: Exception | None = None,
    ):
        super().__init__(message, exception)


class AppStorePrivateKeyMissingException(AppStoreException):
    """
    Exception raised when the App Store private key is missing
    """

    def __init__(
        self,
        message="App Store private key is missing or invalid",
        exception: Exception | None = None,
    ):
        super().__init__(message, exception)


class AppStoreInvalidCredentialsException(AppStoreException):
    """
    Exception raised when the App Store credentials are invalid
    """

    def __init__(
        self,
        message="App Store credentials are invalid",
        exception: Exception | None = None,
    ):
        super().__init__(message, exception)


class AppStoreConnectionAbortedException(AppStoreException):
    """
    Exception raised when the App Store connection is aborted
    """

    def __init__(
        self,
        message="App Store connection aborted",
        exception: Exception | None = None,
    ):
        super().__init__(message, exception)


class AppStoreConnectionRefusedException(AppStoreException):
    """
    Exception raised when the App Store connection is refused
    """

    def __init__(
        self,
        message="App Store connection refused",
        exception: Exception | None = None,
    ):
        super().__init__(message, exception)


class AppStoreRateLimitExceededException(AppStoreException):
    """
    Exception raised when the App Store connection is rate-limited
    """

    def __init__(
        self,
        message="App Store connection rate-limited",
        exception: Exception | None = None,
    ):
        super().__init__(message, exception)


class AppStoreTimeoutException(AppStoreException):
    """
    Exception raised when the App Store connection times out
    """

    def __init__(
        self,
        message="App Store connection timed out",
        exception: Exception | None = None,
    ):
        super().__init__(message, exception)


class AppStoreConnectionErrorException(AppStoreException):
    """
    Exception raised when there is a connection error with the App Store
    """

    def __init__(
        self,
        message="App Store connection error",
        exception: Exception | None = None,
    ):
        super().__init__(message, exception)


class AppStoreResponseException(AppStoreException):
    """
    Exception raised for errors in the App Store response
    """

    def __init__(
        self,
        message="App Store response error",
        exception: Exception | None = None,
    ):
        super().__init__(message, exception)


class AppStoreValidationException(AppStoreException):
    """
    Exception raised for validation errors with App Store data
    """

    def __init__(
        self,
        message="App Store validation error",
        exception: Exception | None = None,
    ):
        super().__init__(message, exception)
