from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.models.ExtendReasonCode import ExtendReasonCode
from faker import Faker

from app.schemas import ApplePayStoreCredentials


@pytest.fixture
def faker_instance() -> Faker:
    """Create a Faker instance for test data generation."""
    return Faker()


# ==================== Apple Pay Credentials Fixtures ====================


@pytest.fixture
def apple_pay_credentials(faker_instance: Faker) -> ApplePayStoreCredentials:
    """Create mock Apple Pay Store credentials."""
    private_key = f"""-----BEGIN REPLACE_ME-----
{faker_instance.sha256()}
{faker_instance.sha256()}
-----END REPLACE_ME-----""".replace(
        "REPLACE_ME", "PRIVATE KEY"
    )

    return ApplePayStoreCredentials(
        private_key=private_key,
        key_id=faker_instance.lexify(
            text="??????????", letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        ),
        issuer_id=faker_instance.uuid4(),
        bundle_id=f"com.{faker_instance.company().lower().replace(' ', '')}.{faker_instance.word()}",
    )


@pytest.fixture
def apple_pay_credentials_dict(apple_pay_credentials: ApplePayStoreCredentials) -> dict:
    """Return Apple Pay credentials as dictionary."""
    return apple_pay_credentials.model_dump()


# ==================== Apple Pay Client Mocks ====================


@pytest.fixture
def mock_apple_pay_client() -> AsyncMock:
    """Create mock AsyncAppStoreServerAPIClient."""
    mock_client = AsyncMock()
    mock_client.get_transaction_info = AsyncMock()
    mock_client.get_transaction_history = AsyncMock()
    mock_client.get_all_subscription_statuses = AsyncMock()
    mock_client.get_refund_history = AsyncMock()
    mock_client.extend_subscription_renewal_date = AsyncMock()
    return mock_client


@pytest.fixture
def mock_signed_data_verifier() -> Mock:
    """Create mock SignedDataVerifier."""
    mock_verifier = Mock()
    mock_verifier.verify_and_decode_signed_transaction = Mock()
    mock_verifier.verify_and_decode_notification = Mock()
    return mock_verifier


# ==================== Apple Pay Response Models ====================


@pytest.fixture
def mock_transaction_info_response(faker_instance: Faker) -> Mock:
    """Create mock TransactionInfoResponse."""
    mock_response = Mock()
    # Simulated signed JWT transaction info
    mock_response.signedTransactionInfo = (
        f"eyJhbGc.{faker_instance.sha256()}.{faker_instance.sha256()}"
    )
    return mock_response


@pytest.fixture
def mock_jws_transaction_decoded(faker_instance: Faker) -> Mock:
    """Create mock JWSTransactionDecodedPayload."""
    mock_transaction = Mock()
    mock_transaction.transactionId = str(
        faker_instance.random_int(min=1000000000000000, max=9999999999999999)
    )
    mock_transaction.originalTransactionId = str(
        faker_instance.random_int(min=1000000000000000, max=9999999999999999)
    )
    mock_transaction.productId = f"com.{faker_instance.word()}.subscription.monthly"
    mock_transaction.bundleId = f"com.{faker_instance.company().lower().replace(' ', '')}.app"
    mock_transaction.purchaseDate = int(datetime.now(UTC).timestamp() * 1000)
    mock_transaction.expiresDate = int((datetime.now(UTC) + timedelta(days=30)).timestamp() * 1000)
    mock_transaction.quantity = 1
    mock_transaction.type = "Auto-Renewable Subscription"
    mock_transaction.inAppOwnershipType = "PURCHASED"
    mock_transaction.signedDate = int(datetime.now(UTC).timestamp() * 1000)
    mock_transaction.environment = Environment.PRODUCTION
    return mock_transaction


@pytest.fixture
def mock_history_response(faker_instance: Faker) -> Mock:
    """Create mock HistoryResponse."""
    mock_response = Mock()
    mock_response.revision = faker_instance.uuid4()
    mock_response.hasMore = False
    mock_response.bundleId = f"com.{faker_instance.company().lower().replace(' ', '')}.app"
    mock_response.appAppleId = faker_instance.random_int(min=100000000, max=999999999)
    mock_response.environment = Environment.PRODUCTION

    # Create list of signed transactions
    signed_transactions = [
        f"eyJhbGc.{faker_instance.sha256()}.{faker_instance.sha256()}" for _ in range(3)
    ]
    mock_response.signedTransactions = signed_transactions

    return mock_response


@pytest.fixture
def mock_status_response(faker_instance: Faker) -> Mock:
    """Create mock StatusResponse."""
    mock_response = Mock()
    mock_response.environment = Environment.PRODUCTION
    mock_response.bundleId = f"com.{faker_instance.company().lower().replace(' ', '')}.app"
    mock_response.appAppleId = faker_instance.random_int(min=100000000, max=999999999)

    # Create mock subscription group status
    mock_subscription_group = Mock()
    mock_subscription_group.subscriptionGroupIdentifier = faker_instance.uuid4()

    # Create mock last transactions
    mock_last_transaction = Mock()
    mock_last_transaction.status = 1  # Active
    mock_last_transaction.originalTransactionId = str(
        faker_instance.random_int(min=1000000000000000, max=9999999999999999)
    )
    mock_last_transaction.signedTransactionInfo = (
        f"eyJhbGc.{faker_instance.sha256()}.{faker_instance.sha256()}"
    )
    mock_last_transaction.signedRenewalInfo = (
        f"eyJhbGc.{faker_instance.sha256()}.{faker_instance.sha256()}"
    )

    mock_subscription_group.lastTransactions = [mock_last_transaction]
    mock_response.data = [mock_subscription_group]

    return mock_response


@pytest.fixture
def mock_refund_history_response(faker_instance: Faker) -> Mock:
    """Create mock RefundHistoryResponse."""
    mock_response = Mock()
    mock_response.hasMore = False
    mock_response.revision = faker_instance.uuid4()

    # Create list of signed transactions for refunds
    signed_transactions = [
        f"eyJhbGc.{faker_instance.sha256()}.{faker_instance.sha256()}" for _ in range(2)
    ]
    mock_response.signedTransactions = signed_transactions

    return mock_response


@pytest.fixture
def mock_extend_renewal_response(faker_instance: Faker) -> Mock:
    """Create mock ExtendRenewalDateResponse."""
    mock_response = Mock()
    mock_response.originalTransactionId = str(
        faker_instance.random_int(min=1000000000000000, max=9999999999999999)
    )
    mock_response.webOrderLineItemId = faker_instance.uuid4()
    mock_response.success = True
    mock_response.effectiveDate = int((datetime.now(UTC) + timedelta(days=7)).timestamp() * 1000)
    return mock_response


@pytest.fixture
def mock_webhook_notification(faker_instance: Faker) -> Mock:
    """Create mock ResponseBodyV2DecodedPayload for webhook."""
    mock_notification = Mock()
    mock_notification.notificationType = "SUBSCRIBED"
    mock_notification.subtype = "INITIAL_BUY"
    mock_notification.notificationUUID = faker_instance.uuid4()
    mock_notification.version = "2.0"
    mock_notification.signedDate = int(datetime.now(UTC).timestamp() * 1000)

    # Create mock data
    mock_data = Mock()
    mock_data.environment = Environment.PRODUCTION
    mock_data.bundleId = f"com.{faker_instance.company().lower().replace(' ', '')}.app"
    mock_data.bundleVersion = "1.0.0"
    mock_data.signedTransactionInfo = f"eyJhbGc.{faker_instance.sha256()}.{faker_instance.sha256()}"

    mock_notification.data = mock_data

    return mock_notification


# ==================== Apple Pay API Exception Fixtures ====================


@pytest.fixture
def mock_api_exception_404() -> Mock:
    """Create mock APIException for 404 Not Found."""
    from appstoreserverlibrary.api_client import APIException

    mock_exception = Mock(spec=APIException)
    mock_exception.http_status_code = 404
    mock_exception.api_error = None
    mock_exception.raw_api_error = None
    return mock_exception


@pytest.fixture
def mock_api_exception_401() -> Mock:
    """Create mock APIException for 401 Unauthorized."""
    from appstoreserverlibrary.api_client import APIException

    mock_exception = Mock(spec=APIException)
    mock_exception.http_status_code = 401
    mock_exception.api_error = None
    mock_exception.raw_api_error = None
    return mock_exception


@pytest.fixture
def mock_api_exception_429() -> Mock:
    """Create mock APIException for 429 Rate Limit."""
    from appstoreserverlibrary.api_client import APIException

    mock_exception = Mock(spec=APIException)
    mock_exception.http_status_code = 429
    mock_exception.api_error = None
    mock_exception.raw_api_error = None
    return mock_exception


@pytest.fixture
def mock_api_exception_500() -> Mock:
    """Create mock APIException for 500 Server Error."""
    from appstoreserverlibrary.api_client import APIException

    mock_exception = Mock(spec=APIException)
    mock_exception.http_status_code = 500
    mock_exception.api_error = None
    mock_exception.raw_api_error = None
    return mock_exception


@pytest.fixture
def mock_api_exception_400() -> Mock:
    """Create mock APIException for 400 Bad Request."""
    from appstoreserverlibrary.api_client import APIException

    mock_exception = Mock(spec=APIException)
    mock_exception.http_status_code = 400
    mock_exception.api_error = None
    mock_exception.raw_api_error = None
    return mock_exception


# ==================== Helper Fixtures ====================


@pytest.fixture
def sample_transaction_id(faker_instance: Faker) -> str:
    """Generate a sample transaction ID."""
    return str(faker_instance.random_int(min=1000000000000000, max=9999999999999999))


@pytest.fixture
def sample_product_id(faker_instance: Faker) -> str:
    """Generate a sample product ID."""
    return f"com.{faker_instance.word()}.subscription.{faker_instance.random_element(['monthly', 'yearly', 'weekly'])}"


@pytest.fixture
def sample_extend_reason_code() -> ExtendReasonCode:
    """Return a sample extend reason code."""
    return ExtendReasonCode.UNDECLARED


@pytest.fixture
def sample_request_identifier(faker_instance: Faker) -> str:
    """Generate a sample request identifier."""
    return faker_instance.uuid4()
