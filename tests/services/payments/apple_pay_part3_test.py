"""
Apple Pay Tests - Part 3: Transaction History, Subscription Status, and Refunds

This file contains comprehensive tests for transaction history, subscription status, and refund operations.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from appstoreserverlibrary.api_client import APIException
from faker import Faker

from app.core.exceptions.apple_pay import (
    AppStoreConnectionAbortedException,
    AppStoreConnectionErrorException,
    AppStoreInvalidCredentialsException,
    AppStoreValidationException,
)
from app.schemas import ApplePayStoreCredentials
from app.services.payments.apple_pay import ApplePay


class TestApplePayTransactionHistory:
    """Test transaction history operations."""

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_transaction_history_success(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
        mock_history_response: Mock,
    ):
        """Test successful transaction history retrieval."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get_transaction_history.return_value = mock_history_response
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        result = await apple_pay.get_transaction_history(sample_transaction_id)

        assert result == mock_history_response
        mock_client_instance.get_transaction_history.assert_called_once()

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_transaction_history_with_revision(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
        mock_history_response: Mock,
        faker_instance: Faker,
    ):
        """Test transaction history retrieval with revision."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get_transaction_history.return_value = mock_history_response
        mock_client_class.return_value = mock_client_instance
        revision = faker_instance.uuid4()

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        result = await apple_pay.get_transaction_history(sample_transaction_id, revision=revision)

        assert result == mock_history_response

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_transaction_history_not_found(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
    ):
        """Test get_transaction_history raises NotFoundException for 404."""
        mock_client_instance = AsyncMock()
        mock_api_error = APIException(404, None, None)
        mock_client_instance.get_transaction_history.side_effect = mock_api_error
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        # 404 is treated as ConnectionAborted in transaction history
        with pytest.raises(AppStoreConnectionAbortedException):
            await apple_pay.get_transaction_history(sample_transaction_id)

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_transaction_history_unauthorized(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
    ):
        """Test get_transaction_history raises InvalidCredentialsException for 401."""
        mock_client_instance = AsyncMock()
        mock_api_error = APIException(401, None, None)
        mock_client_instance.get_transaction_history.side_effect = mock_api_error
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreInvalidCredentialsException):
            await apple_pay.get_transaction_history(sample_transaction_id)

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_transaction_history_rate_limit(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
    ):
        """Test get_transaction_history raises RateLimitExceededException for 429."""
        mock_client_instance = AsyncMock()
        mock_api_error = APIException(429, None, None)
        mock_client_instance.get_transaction_history.side_effect = mock_api_error
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        # 429 is treated as ConnectionError in transaction history
        with pytest.raises(AppStoreConnectionErrorException):
            await apple_pay.get_transaction_history(sample_transaction_id)

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_transaction_history_empty_id(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test get_transaction_history raises ValidationException for empty ID."""
        mock_client_class.return_value = AsyncMock()

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreValidationException):
            await apple_pay.get_transaction_history("")


class TestApplePaySubscriptionStatus:
    """Test subscription status operations."""

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_subscription_status_success(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
        mock_status_response: Mock,
    ):
        """Test successful subscription status retrieval."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get_all_subscription_statuses.return_value = mock_status_response
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        result = await apple_pay.get_subscription_status(sample_transaction_id)

        assert result == mock_status_response
        mock_client_instance.get_all_subscription_statuses.assert_called_once_with(
            sample_transaction_id
        )

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_subscription_status_not_found(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
    ):
        """Test get_subscription_status raises NotFoundException for 404."""
        mock_client_instance = AsyncMock()
        mock_api_error = APIException(404, None, None)
        mock_client_instance.get_all_subscription_statuses.side_effect = mock_api_error
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        # 404 is treated as ConnectionAborted in subscription status
        with pytest.raises(AppStoreConnectionAbortedException):
            await apple_pay.get_subscription_status(sample_transaction_id)

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_subscription_status_unauthorized(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
    ):
        """Test get_subscription_status raises InvalidCredentialsException for 401."""
        mock_client_instance = AsyncMock()
        mock_api_error = APIException(401, None, None)
        mock_client_instance.get_all_subscription_statuses.side_effect = mock_api_error
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreInvalidCredentialsException):
            await apple_pay.get_subscription_status(sample_transaction_id)

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_subscription_status_empty_id(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test get_subscription_status raises ValidationException for empty ID."""
        mock_client_class.return_value = AsyncMock()

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreValidationException):
            await apple_pay.get_subscription_status("")


class TestApplePayRefundOperations:
    """Test refund history operations."""

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_refund_history_success(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
        mock_refund_history_response: Mock,
    ):
        """Test successful refund history retrieval."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get_refund_history.return_value = mock_refund_history_response
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        result = await apple_pay.get_refund_history(sample_transaction_id)

        assert result == mock_refund_history_response
        # The method is called with revision=None parameter
        mock_client_instance.get_refund_history.assert_called_once_with(
            sample_transaction_id, revision=None
        )

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_refund_history_not_found(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
    ):
        """Test get_refund_history raises NotFoundException for 404."""
        mock_client_instance = AsyncMock()
        mock_api_error = APIException(404, None, None)
        mock_client_instance.get_refund_history.side_effect = mock_api_error
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        # 404 is treated as ConnectionAborted in refund history
        with pytest.raises(AppStoreConnectionAbortedException):
            await apple_pay.get_refund_history(sample_transaction_id)

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_refund_history_unauthorized(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
    ):
        """Test get_refund_history raises InvalidCredentialsException for 401."""
        mock_client_instance = AsyncMock()
        mock_api_error = APIException(401, None, None)
        mock_client_instance.get_refund_history.side_effect = mock_api_error
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreInvalidCredentialsException):
            await apple_pay.get_refund_history(sample_transaction_id)

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_refund_history_rate_limit(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
    ):
        """Test get_refund_history raises RateLimitExceededException for 429."""
        mock_client_instance = AsyncMock()
        mock_api_error = APIException(429, None, None)
        mock_client_instance.get_refund_history.side_effect = mock_api_error
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        # 429 is treated as ConnectionError in refund history
        with pytest.raises(AppStoreConnectionErrorException):
            await apple_pay.get_refund_history(sample_transaction_id)

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_refund_history_server_error(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
    ):
        """Test get_refund_history raises ConnectionAbortedException for 500."""
        mock_client_instance = AsyncMock()
        mock_api_error = APIException(500, None, None)
        mock_client_instance.get_refund_history.side_effect = mock_api_error
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreConnectionAbortedException):
            await apple_pay.get_refund_history(sample_transaction_id)

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_refund_history_empty_id(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test get_refund_history raises ValidationException for empty ID."""
        mock_client_class.return_value = AsyncMock()

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreValidationException):
            await apple_pay.get_refund_history("")

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_refund_history_generic_exception(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
    ):
        """Test get_refund_history raises ConnectionAbortedException for generic exceptions."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get_refund_history.side_effect = Exception("Unexpected error")
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreConnectionAbortedException):
            await apple_pay.get_refund_history(sample_transaction_id)
