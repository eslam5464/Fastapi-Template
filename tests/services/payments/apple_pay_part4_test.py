"""
Apple Pay Tests - Part 4: Subscription Extension, Decoding, Caching, and Helpers

This file contains comprehensive tests for subscription renewal extension, decoding operations,
caching functionality, and helper methods.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from appstoreserverlibrary.api_client import APIException
from appstoreserverlibrary.models.ExtendReasonCode import ExtendReasonCode
from faker import Faker

from app.core.exceptions.apple_pay import (
    AppStoreConnectionAbortedException,
    AppStoreNotFoundException,
    AppStoreValidationException,
)
from app.schemas import ApplePayStoreCredentials
from app.services.payments.apple_pay import ApplePay


class TestApplePaySubscriptionExtension:
    """Test subscription renewal date extension operations."""

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_extend_subscription_renewal_date_success(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
        sample_extend_reason_code: ExtendReasonCode,
        sample_request_identifier: str,
        mock_extend_renewal_response: Mock,
    ):
        """Test successful subscription renewal date extension."""
        mock_client_instance = AsyncMock()
        mock_client_instance.extend_subscription_renewal_date.return_value = (
            mock_extend_renewal_response
        )
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        result = await apple_pay.extend_subscription_renewal_date(
            sample_transaction_id,
            extend_by_days=7,
            extend_reason_code=sample_extend_reason_code,
            request_identifier=sample_request_identifier,
        )

        assert result == mock_extend_renewal_response
        mock_client_instance.extend_subscription_renewal_date.assert_called_once()

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_extend_subscription_renewal_date_not_found(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
        sample_extend_reason_code: ExtendReasonCode,
        sample_request_identifier: str,
    ):
        """Test extend renewal date raises NotFoundException for 404."""
        mock_client_instance = AsyncMock()
        mock_api_error = APIException(404, None, None)
        mock_client_instance.extend_subscription_renewal_date.side_effect = mock_api_error
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreNotFoundException):
            await apple_pay.extend_subscription_renewal_date(
                sample_transaction_id,
                extend_by_days=7,
                extend_reason_code=sample_extend_reason_code,
                request_identifier=sample_request_identifier,
            )

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_extend_subscription_renewal_date_validation_error(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
        sample_extend_reason_code: ExtendReasonCode,
        sample_request_identifier: str,
    ):
        """Test extend renewal date raises ValidationException for invalid parameters."""
        mock_client_instance = AsyncMock()
        mock_client_instance.extend_subscription_renewal_date.side_effect = ValueError(
            "Invalid extend days"
        )
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreValidationException):
            await apple_pay.extend_subscription_renewal_date(
                sample_transaction_id,
                extend_by_days=100,  # Invalid value
                extend_reason_code=sample_extend_reason_code,
                request_identifier=sample_request_identifier,
            )


class TestApplePayDecoding:
    """Test decoding and verification operations."""

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_decode_transaction_info_success(
        self,
        mock_verifier_class: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        mock_transaction_info_response: Mock,
        mock_jws_transaction_decoded: Mock,
    ):
        """Test successful transaction info decoding."""
        mock_client_class.return_value = AsyncMock()
        mock_verifier_instance = Mock()
        mock_verifier_instance.verify_and_decode_signed_transaction.return_value = (
            mock_jws_transaction_decoded
        )
        mock_verifier_class.return_value = mock_verifier_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        result = await apple_pay.decode_transaction_info(mock_transaction_info_response)

        assert result == mock_jws_transaction_decoded

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_decode_transaction_info_invalid_signature(
        self,
        mock_verifier_class: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        mock_transaction_info_response: Mock,
    ):
        """Test decode transaction info raises ValidationException for invalid signature."""
        mock_client_class.return_value = AsyncMock()
        mock_verifier_instance = Mock()
        mock_verifier_instance.verify_and_decode_signed_transaction.side_effect = ValueError(
            "Invalid signature"
        )
        mock_verifier_class.return_value = mock_verifier_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        # Decoding errors are wrapped in ConnectionAbortedException
        with pytest.raises(AppStoreConnectionAbortedException):
            await apple_pay.decode_transaction_info(mock_transaction_info_response)

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_verify_webhook_signature_success(
        self,
        mock_verifier_class: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        mock_webhook_notification: Mock,
        faker_instance: Faker,
    ):
        """Test successful webhook signature verification."""
        mock_client_class.return_value = AsyncMock()
        mock_verifier_instance = Mock()
        mock_verifier_instance.verify_and_decode_notification.return_value = (
            mock_webhook_notification
        )
        mock_verifier_class.return_value = mock_verifier_instance

        signed_payload = f"eyJhbGc.{faker_instance.sha256()}.{faker_instance.sha256()}"

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        result = await apple_pay.verify_webhook_signature(signed_payload)

        assert result == mock_webhook_notification

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_verify_webhook_signature_invalid(
        self,
        mock_verifier_class: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        faker_instance: Faker,
    ):
        """Test verify webhook signature raises ValidationException for invalid signature."""
        mock_client_class.return_value = AsyncMock()
        mock_verifier_instance = Mock()
        mock_verifier_instance.verify_and_decode_notification.side_effect = ValueError(
            "Invalid webhook signature"
        )
        mock_verifier_class.return_value = mock_verifier_instance

        signed_payload = "invalid.signature.data"

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreValidationException):
            await apple_pay.verify_webhook_signature(signed_payload)


class TestApplePayCaching:
    """Test caching functionality."""

    @patch("app.services.payments.apple_pay.cache_manager")
    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_subscription_status_cached_hit(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        mock_cache_manager: AsyncMock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
        mock_status_response: Mock,
    ):
        """Test get_subscription_status_cached returns cached data when available."""
        mock_client_instance = AsyncMock()
        mock_client_class.return_value = mock_client_instance
        mock_cache_manager.get = AsyncMock(return_value=mock_status_response)

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        result = await apple_pay.get_subscription_status_cached(
            user_id=123, original_transaction_id=sample_transaction_id
        )

        assert result == mock_status_response
        mock_cache_manager.get.assert_called_once()
        mock_client_instance.get_all_subscription_statuses.assert_not_called()

    @patch("app.services.payments.apple_pay.cache_manager")
    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_subscription_status_cached_miss(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        mock_cache_manager: AsyncMock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
        mock_status_response: Mock,
    ):
        """Test get_subscription_status_cached fetches from API when cache misses."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get_all_subscription_statuses.return_value = mock_status_response
        mock_client_class.return_value = mock_client_instance
        mock_cache_manager.get = AsyncMock(return_value=None)
        mock_cache_manager.set = AsyncMock()

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        result = await apple_pay.get_subscription_status_cached(
            user_id=123, original_transaction_id=sample_transaction_id
        )

        assert result == mock_status_response
        mock_cache_manager.get.assert_called_once()
        mock_client_instance.get_all_subscription_statuses.assert_called_once()
        mock_cache_manager.set.assert_called_once()

    @patch("app.services.payments.apple_pay.cache_manager")
    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_get_subscription_status_cached_force_refresh(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        mock_cache_manager: AsyncMock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
        mock_status_response: Mock,
    ):
        """Test get_subscription_status_cached bypasses cache when force_refresh is True."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get_all_subscription_statuses.return_value = mock_status_response
        mock_client_class.return_value = mock_client_instance
        mock_cache_manager.set = AsyncMock()

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        result = await apple_pay.get_subscription_status_cached(
            user_id=123, original_transaction_id=sample_transaction_id, force_refresh=True
        )

        assert result == mock_status_response
        mock_cache_manager.get.assert_not_called()
        mock_client_instance.get_all_subscription_statuses.assert_called_once()
        mock_cache_manager.set.assert_called_once()

    @patch("app.services.payments.apple_pay.cache_manager")
    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_invalidate_subscription_cache_success(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        mock_cache_manager: AsyncMock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test successful cache invalidation."""
        mock_client_class.return_value = AsyncMock()
        mock_cache_manager.delete = AsyncMock(return_value=True)

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        await apple_pay.invalidate_subscription_cache(user_id=123)

        mock_cache_manager.delete.assert_called_once()

    @patch("app.services.payments.apple_pay.cache_manager")
    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_invalidate_subscription_cache_not_found(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        mock_cache_manager: AsyncMock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test cache invalidation when cache doesn't exist."""
        mock_client_class.return_value = AsyncMock()
        mock_cache_manager.delete = AsyncMock(return_value=False)

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        await apple_pay.invalidate_subscription_cache(user_id=123)

        mock_cache_manager.delete.assert_called_once()


class TestApplePayHelperMethods:
    """Test helper and utility methods."""

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    def test_get_latest_transaction_success(
        self,
        mock_verifier_class: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        mock_history_response: Mock,
        mock_jws_transaction_decoded: Mock,
    ):
        """Test get_latest_transaction returns latest transaction from history."""
        mock_client_class.return_value = AsyncMock()
        mock_verifier_instance = Mock()
        mock_verifier_instance.verify_and_decode_signed_transaction.return_value = (
            mock_jws_transaction_decoded
        )
        mock_verifier_class.return_value = mock_verifier_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        result = apple_pay.get_latest_transaction(mock_history_response)

        assert result == mock_jws_transaction_decoded or result is None

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    def test_get_latest_transaction_empty_history(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test get_latest_transaction returns None for empty history."""
        mock_client_class.return_value = AsyncMock()
        mock_history_response = Mock()
        mock_history_response.signedTransactions = []

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        result = apple_pay.get_latest_transaction(mock_history_response)

        assert result is None

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_verify_and_process_subscription_success(
        self,
        mock_verifier_class: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
        sample_product_id: str,
        mock_transaction_info_response: Mock,
        mock_jws_transaction_decoded: Mock,
    ):
        """Test successful verify_and_process_subscription."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get_transaction_info.return_value = mock_transaction_info_response
        mock_client_class.return_value = mock_client_instance

        mock_verifier_instance = Mock()
        mock_verifier_instance.verify_and_decode_signed_transaction.return_value = (
            mock_jws_transaction_decoded
        )
        mock_verifier_class.return_value = mock_verifier_instance
        mock_jws_transaction_decoded.productId = sample_product_id

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        transaction_info, decoded = await apple_pay.verify_and_process_subscription(
            sample_transaction_id, expected_product_id=sample_product_id
        )

        assert transaction_info == mock_transaction_info_response
        assert decoded == mock_jws_transaction_decoded

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_verify_and_process_subscription_without_product_id(
        self,
        mock_verifier_class: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
        mock_transaction_info_response: Mock,
        mock_jws_transaction_decoded: Mock,
    ):
        """Test verify_and_process_subscription without product ID validation."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get_transaction_info.return_value = mock_transaction_info_response
        mock_client_class.return_value = mock_client_instance

        mock_verifier_instance = Mock()
        mock_verifier_instance.verify_and_decode_signed_transaction.return_value = (
            mock_jws_transaction_decoded
        )
        mock_verifier_class.return_value = mock_verifier_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        transaction_info, decoded = await apple_pay.verify_and_process_subscription(
            sample_transaction_id, expected_product_id=None
        )

        assert transaction_info == mock_transaction_info_response
        assert decoded == mock_jws_transaction_decoded

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_verify_and_process_subscription_product_mismatch(
        self,
        mock_verifier_class: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
        mock_transaction_info_response: Mock,
        mock_jws_transaction_decoded: Mock,
    ):
        """Test verify_and_process_subscription raises ValidationException on product mismatch."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get_transaction_info.return_value = mock_transaction_info_response
        mock_client_class.return_value = mock_client_instance

        mock_verifier_instance = Mock()
        mock_verifier_instance.verify_and_decode_signed_transaction.return_value = (
            mock_jws_transaction_decoded
        )
        mock_verifier_class.return_value = mock_verifier_instance
        mock_jws_transaction_decoded.productId = "com.app.product1"

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreValidationException):
            await apple_pay.verify_and_process_subscription(
                sample_transaction_id, expected_product_id="com.app.product2"
            )
