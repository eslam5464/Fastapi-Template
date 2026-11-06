"""
Apple Pay Tests: cached subscription status (needs the Redis cache).
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.credentials.apple_pay import ApplePayStoreCredentials
from app.services.payments.apple_pay import ApplePay


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
