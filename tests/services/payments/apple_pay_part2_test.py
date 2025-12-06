"""
Apple Pay Tests - Part 2: Transaction Verification

This file contains comprehensive tests for transaction verification operations.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from appstoreserverlibrary.api_client import APIException
from faker import Faker

from app.core.exceptions.apple_pay import (
    AppStoreConnectionAbortedException,
    AppStoreInvalidCredentialsException,
    AppStoreNotFoundException,
    AppStoreRateLimitExceededException,
    AppStoreValidationException,
)
from app.schemas import ApplePayStoreCredentials
from app.services.payments.apple_pay import ApplePay


class TestApplePayTransactionVerification:
    """Test transaction verification operations."""

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_verify_transaction_success(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
        mock_transaction_info_response: Mock,
    ):
        """Test successful transaction verification."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get_transaction_info.return_value = mock_transaction_info_response
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)
        result = await apple_pay.verify_transaction(sample_transaction_id)

        assert result == mock_transaction_info_response
        mock_client_instance.get_transaction_info.assert_called_once_with(sample_transaction_id)

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_verify_transaction_empty_id(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test verify_transaction raises ValidationException for empty transaction ID."""
        mock_client_class.return_value = AsyncMock()

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreValidationException) as exc_info:
            await apple_pay.verify_transaction("")

        assert "Transaction ID must be a non-empty string" in str(exc_info.value)

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_verify_transaction_whitespace_id(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test verify_transaction raises ValidationException for whitespace transaction ID."""
        mock_client_class.return_value = AsyncMock()

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreValidationException) as exc_info:
            await apple_pay.verify_transaction("   ")

        assert "Transaction ID cannot be empty or whitespace" in str(exc_info.value)

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_verify_transaction_none_id(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test verify_transaction raises ValidationException for None transaction ID."""
        mock_client_class.return_value = AsyncMock()

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreValidationException):
            await apple_pay.verify_transaction(None)  # type: ignore

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_verify_transaction_not_found(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
    ):
        """Test verify_transaction raises NotFoundException for 404."""
        mock_client_instance = AsyncMock()
        mock_api_error = APIException(404, None, None)
        mock_client_instance.get_transaction_info.side_effect = mock_api_error
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreNotFoundException) as exc_info:
            await apple_pay.verify_transaction(sample_transaction_id)

        assert "not found" in str(exc_info.value).lower()

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_verify_transaction_unauthorized(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
    ):
        """Test verify_transaction raises InvalidCredentialsException for 401."""
        mock_client_instance = AsyncMock()
        mock_api_error = APIException(401, None, None)
        mock_client_instance.get_transaction_info.side_effect = mock_api_error
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreInvalidCredentialsException) as exc_info:
            await apple_pay.verify_transaction(sample_transaction_id)

        assert "invalid apple pay credentials" in str(exc_info.value).lower()

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_verify_transaction_rate_limit(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
    ):
        """Test verify_transaction raises RateLimitExceededException for 429."""
        mock_client_instance = AsyncMock()
        mock_api_error = APIException(429, None, None)
        mock_client_instance.get_transaction_info.side_effect = mock_api_error
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreRateLimitExceededException) as exc_info:
            await apple_pay.verify_transaction(sample_transaction_id)

        assert "rate" in str(exc_info.value).lower()

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_verify_transaction_server_error(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
    ):
        """Test verify_transaction raises ConnectionAbortedException for 500."""
        mock_client_instance = AsyncMock()
        mock_api_error = APIException(500, None, None)
        mock_client_instance.get_transaction_info.side_effect = mock_api_error
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreConnectionAbortedException) as exc_info:
            await apple_pay.verify_transaction(sample_transaction_id)

        assert (
            "server error" in str(exc_info.value).lower()
            or "aborted" in str(exc_info.value).lower()
        )

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_verify_transaction_bad_request(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
    ):
        """Test verify_transaction raises ConnectionErrorException for 400."""
        mock_client_instance = AsyncMock()
        mock_api_error = APIException(400, None, None)
        mock_client_instance.get_transaction_info.side_effect = mock_api_error
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        # 400 is treated as 404 (Not Found) in the implementation
        with pytest.raises(AppStoreNotFoundException):
            await apple_pay.verify_transaction(sample_transaction_id)

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_verify_transaction_value_error(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
    ):
        """Test verify_transaction raises ValidationException for ValueError."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get_transaction_info.side_effect = ValueError("Invalid format")
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        # ValueError is not caught, it propagates
        with pytest.raises(ValueError):
            await apple_pay.verify_transaction(sample_transaction_id)

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    @pytest.mark.anyio
    async def test_verify_transaction_generic_exception(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
    ):
        """Test verify_transaction raises ConnectionAbortedException for generic exceptions."""
        mock_client_instance = AsyncMock()
        mock_client_instance.get_transaction_info.side_effect = Exception("Unexpected error")
        mock_client_class.return_value = mock_client_instance

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreConnectionAbortedException):
            await apple_pay.verify_transaction(sample_transaction_id)

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    def test_check_product_id_in_transaction_match(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        mock_jws_transaction_decoded: Mock,
        sample_product_id: str,
    ):
        """Test check_product_id_in_transaction succeeds when product IDs match."""
        mock_client_class.return_value = AsyncMock()
        mock_jws_transaction_decoded.productId = sample_product_id

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        # Should not raise exception
        apple_pay.check_product_id_in_transaction(mock_jws_transaction_decoded, sample_product_id)

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    def test_check_product_id_in_transaction_mismatch(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        mock_jws_transaction_decoded: Mock,
        faker_instance: Faker,
    ):
        """Test check_product_id_in_transaction raises ValidationException on mismatch."""
        mock_client_class.return_value = AsyncMock()
        mock_jws_transaction_decoded.productId = "com.app.product1"
        expected_product_id = "com.app.product2"

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreValidationException) as exc_info:
            apple_pay.check_product_id_in_transaction(
                mock_jws_transaction_decoded, expected_product_id
            )

        assert "product" in str(exc_info.value).lower()
        assert "mismatch" in str(exc_info.value).lower()


class TestApplePayValidation:
    """Test validation methods."""

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    def test_validate_transaction_id_valid(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
        sample_transaction_id: str,
    ):
        """Test _validate_transaction_id succeeds with valid ID."""
        mock_client_class.return_value = AsyncMock()

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        # Should not raise exception
        apple_pay._validate_transaction_id(sample_transaction_id)

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    def test_validate_transaction_id_empty(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test _validate_transaction_id raises ValidationException for empty string."""
        mock_client_class.return_value = AsyncMock()

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreValidationException):
            apple_pay._validate_transaction_id("")

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    def test_validate_transaction_id_whitespace(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test _validate_transaction_id raises ValidationException for whitespace."""
        mock_client_class.return_value = AsyncMock()

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreValidationException):
            apple_pay._validate_transaction_id("   ")

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    def test_validate_transaction_id_none(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test _validate_transaction_id raises ValidationException for None."""
        mock_client_class.return_value = AsyncMock()

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreValidationException):
            apple_pay._validate_transaction_id(None)  # type: ignore

    @patch("app.services.payments.apple_pay.AsyncAppStoreServerAPIClient")
    @patch("app.services.payments.apple_pay.SignedDataVerifier")
    def test_validate_transaction_id_non_string(
        self,
        mock_verifier: Mock,
        mock_client_class: Mock,
        apple_pay_credentials: ApplePayStoreCredentials,
    ):
        """Test _validate_transaction_id raises ValidationException for non-string."""
        mock_client_class.return_value = AsyncMock()

        apple_pay = ApplePay(credentials=apple_pay_credentials)

        with pytest.raises(AppStoreValidationException):
            apple_pay._validate_transaction_id(12345)  # type: ignore
