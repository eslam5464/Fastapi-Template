from app.core.exceptions.base import AppException


class FirebaseError(AppException):
    """
    Base exception for Firebase
    """

    def __init__(self, message, exception: Exception | None = None):
        super().__init__(message, exception)


class FirebaseAuthenticationError(FirebaseError):
    """
    Authentication error for Firebase
    """

    def __init__(self, message, exception: Exception | None = None):
        super().__init__(message, exception)


class FirebaseFirestoreError(FirebaseError):
    """
    Firestore operation error for Firebase
    """

    def __init__(self, message, exception: Exception | None = None):
        super().__init__(message, exception)


class FirebaseDocumentNotFoundError(FirebaseFirestoreError):
    """
    Document not found error in Firestore
    """

    def __init__(self, message, exception: Exception | None = None):
        super().__init__(message, exception)
