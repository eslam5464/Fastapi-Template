"""Firebase fixtures, shared by the tests in this package."""

from unittest.mock import Mock

import pytest
from faker import Faker
from firebase_admin import App
from firebase_admin.auth import ListUsersPage, UserRecord
from firebase_admin.messaging import BatchResponse, SendResponse

from app.core.credentials.firebase import FirebaseServiceAccount


@pytest.fixture
def firebase_service_account(faker_instance: Faker) -> FirebaseServiceAccount:
    """Create mock Firebase service account credentials."""
    return FirebaseServiceAccount(
        type="service_account",
        project_id=faker_instance.word(),
        private_key_id=faker_instance.uuid4(),
        private_key=f"-----BEGIN ##$$##-----\n{faker_instance.sha256()}\n-----END ##$$##-----".replace(
            "##$$##", "PRIVATE KEY"
        ),
        client_email=faker_instance.email(),
        client_id=faker_instance.uuid4(),
        auth_uri="https://accounts.google.com/o/oauth2/auth",
        token_uri="https://oauth2.googleapis.com/token",
        auth_provider_x509_cert_url="https://www.googleapis.com/oauth2/v1/certs",
        client_x509_cert_url=faker_instance.url(),
        universe_domain="googleapis.com",
    )


@pytest.fixture
def mock_firebase_app() -> Mock:
    """Create a mock Firebase App instance."""
    return Mock(spec=App)


@pytest.fixture
def mock_user_record(faker_instance: Faker) -> Mock:
    """Create a mock Firebase UserRecord."""
    mock_user = Mock(spec=UserRecord)
    mock_user.uid = faker_instance.uuid4()
    mock_user.email = faker_instance.email()
    mock_user.display_name = faker_instance.name()
    mock_user.phone_number = faker_instance.phone_number()
    return mock_user


@pytest.fixture
def mock_list_users_page() -> Mock:
    """Create a mock ListUsersPage."""
    return Mock(spec=ListUsersPage)


@pytest.fixture
def mock_batch_response() -> Mock:
    """Create a mock BatchResponse for FCM."""
    mock_response = Mock(spec=BatchResponse)
    mock_response.success_count = 5
    mock_response.failure_count = 0
    mock_response.responses = [Mock(spec=SendResponse, success=True) for _ in range(5)]
    return mock_response
