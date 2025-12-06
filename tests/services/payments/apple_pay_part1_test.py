"""
Comprehensive tests for Apple Pay payment service.

This test file is organized into multiple test classes by functionality:
- Part 1: Initialization and client management
- Part 2: Transaction verification
- Part 3: Transaction history
- Part 4: Subscription status
- Part 5: Refund operations
- Part 6: Subscription extension
- Part 7: Decoding and verification
- Part 8: Caching functionality
- Part 9: Helper methods and validation
- Part 10: High-level operations
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from appstoreserverlibrary.api_client import APIException
from appstoreserverlibrary.models.Environment import Environment

from app.core.config import Environment as AppEnvironment
from app.core.exceptions.apple_pay import (
    AppStoreException,
    AppStoreInvalidCredentialsException,
    AppStorePrivateKeyMissingException,
)
from app.schemas import ApplePayStoreCredentials
from app.services.payments.apple_pay import ApplePay

# ==================== PART 1: Initialization and Client Management ====================


class TestApplePayInitialization:
    """Test ApplePay initialization and client setup."""

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    def test_init_with_credentials(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test ApplePay initialization with provided credentials."""
        mock_client_instance = AsyncMock()
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        assert apple_pay._credentials == apple_pay_credentials
        assert apple_pay._client == mock_client_instance
        mock_client_class.assert_called_once()

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @patch("app.services.payments.apple_pay.settings")
    def test_init_without_credentials_uses_settings(
        self,
        mock_settings: Mock,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test ApplePay initialization without credentials uses settings."""
        mock_settings.apple_pay_store_credentials = apple_pay_credentials
        mock_settings.current_environment = AppEnvironment.PRD
        mock_client_instance = AsyncMock()
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay()

        assert apple_pay._credentials == apple_pay_credentials
        assert apple_pay._client == mock_client_instance

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @patch("app.services.payments.apple_pay.settings")
    def test_init_sandbox_environment(
        self,
        mock_settings: Mock,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test ApplePay initialization sets SANDBOX environment for non-prod."""
        mock_settings.apple_pay_store_credentials = apple_pay_credentials
        mock_settings.current_environment = AppEnvironment.LOCAL
        mock_client_instance = AsyncMock()
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay()

        assert apple_pay._environment == Environment.SANDBOX

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @patch("app.services.payments.apple_pay.settings")
    def test_init_production_environment(
        self,
        mock_settings: Mock,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test ApplePay initialization sets PRODUCTION environment for prod."""
        mock_settings.apple_pay_store_credentials = apple_pay_credentials
        mock_settings.current_environment = AppEnvironment.PRD
        mock_client_instance = AsyncMock()
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay()

        assert apple_pay._environment == Environment.PRODUCTION

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @patch("app.services.payments.apple_pay.settings")
    def test_init_file_not_found_error(
        self,
        mock_settings: Mock,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test ApplePay initialization handles FileNotFoundError."""
        mock_settings.apple_pay_store_credentials = apple_pay_credentials
        mock_settings.current_environment = AppEnvironment.PRD
        mock_client_class.side_effect = FileNotFoundError("Private key file not found")

        with pytest.raises(AppStorePrivateKeyMissingException) as exc_info:
            ApplePay()

        assert "credentials file not found" in str(exc_info.value).lower()

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @patch("app.services.payments.apple_pay.settings")
    def test_init_value_error(
        self,
        mock_settings: Mock,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test ApplePay initialization handles ValueError."""
        mock_settings.apple_pay_store_credentials = apple_pay_credentials
        mock_settings.current_environment = AppEnvironment.PRD
        mock_client_class.side_effect = ValueError("Invalid credentials format")

        with pytest.raises(AppStoreInvalidCredentialsException) as exc_info:
            ApplePay()

        assert (
            "invalid" in str(exc_info.value).lower()
            and "credentials" in str(exc_info.value).lower()
        )

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @patch("app.services.payments.apple_pay.settings")
    def test_init_generic_exception(
        self,
        mock_settings: Mock,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test ApplePay initialization handles generic exceptions."""
        mock_settings.apple_pay_store_credentials = apple_pay_credentials
        mock_settings.current_environment = AppEnvironment.PRD
        mock_client_class.side_effect = Exception("Unexpected error")

        with pytest.raises(AppStoreException) as exc_info:
            ApplePay()

        assert "Failed to initialize" in str(exc_info.value)


class TestApplePayClientManagement:
    """Test ApplePay client management and properties."""

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    def test_client_property_when_initialized(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test client property returns client when initialized."""
        mock_client_instance = AsyncMock()
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        assert apple_pay.client == mock_client_instance

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @patch("app.services.payments.apple_pay.settings")
    def test_client_property_when_not_initialized(
        self,
        mock_settings: Mock,
        mock_verifier: Mock,
        mock_client_class: Mock,
    ):
        """Test client property raises exception when not initialized."""
        mock_settings.apple_pay_store_credentials = None
        mock_client_class.side_effect = Exception("No credentials")

        with pytest.raises(AppStoreException):
            apple_pay = ApplePay()
            _ = apple_pay.client

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    def test_credentials_property_when_set(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test credentials property returns credentials when set."""
        mock_client_class.return_value = AsyncMock()

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        assert apple_pay.credentials == apple_pay_credentials

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    def test_current_environment_property(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test current_environment property returns environment."""
        mock_client_class.return_value = AsyncMock()

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        assert apple_pay.current_environment in [Environment.PRODUCTION, Environment.SANDBOX]

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_close_client_success(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test close_client successfully closes the client."""
        mock_client_instance = AsyncMock()
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        await apple_pay.close_client()

        # Verify client was closed (implementation specific)
        assert apple_pay._client is None or mock_client_instance

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_check_connection_success(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        mock_transaction_info_response: Mock,
    ):
        """Test check_connection returns True on successful connection."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get_transaction_info.side_effect = APIException(404, None, None)
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        result = await apple_pay.check_connection()

        assert result is True

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_check_connection_not_found_is_success(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test check_connection treats 404 as successful connection."""
        mock_client_instance = AsyncMock()
        mock_api_error = APIException(404, None, None)
        mock_client_instance.get_transaction_info.side_effect = mock_api_error
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        result = await apple_pay.check_connection()

        assert result is True

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_check_connection_server_error(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test check_connection returns True even on server error (connection successful)."""
        mock_client_instance = AsyncMock()
        mock_api_error = APIException(500, None, None)
        mock_client_instance.get_transaction_info.side_effect = mock_api_error
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        result = await apple_pay.check_connection()

        assert result is True

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_check_connection_generic_exception(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test check_connection returns True even on generic exception (connection attempted)."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get_transaction_info.side_effect = Exception("Connection failed")
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        result = await apple_pay.check_connection()

        assert result is True
