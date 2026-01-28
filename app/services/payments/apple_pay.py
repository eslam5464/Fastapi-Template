from dataclasses import dataclass, field

from appstoreserverlibrary.api_client import APIException, AsyncAppStoreServerAPIClient
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.models.ExtendReasonCode import ExtendReasonCode
from appstoreserverlibrary.models.ExtendRenewalDateRequest import (
    ExtendRenewalDateRequest,
)
from appstoreserverlibrary.models.ExtendRenewalDateResponse import (
    ExtendRenewalDateResponse,
)
from appstoreserverlibrary.models.HistoryResponse import HistoryResponse
from appstoreserverlibrary.models.JWSTransactionDecodedPayload import JWSTransactionDecodedPayload
from appstoreserverlibrary.models.RefundHistoryResponse import RefundHistoryResponse
from appstoreserverlibrary.models.ResponseBodyV2DecodedPayload import ResponseBodyV2DecodedPayload
from appstoreserverlibrary.models.StatusResponse import StatusResponse
from appstoreserverlibrary.models.TransactionHistoryRequest import (
    TransactionHistoryRequest,
)
from appstoreserverlibrary.models.TransactionInfoResponse import (
    TransactionInfoResponse,
)
from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier
from loguru import logger

from app.core.config import Environment as AppEnvironment, settings
from app.core.exceptions.apple_pay import (
    AppStoreClientNotInitializedException,
    AppStoreConnectionAbortedException,
    AppStoreConnectionErrorException,
    AppStoreException,
    AppStoreInvalidCredentialsException,
    AppStoreNotFoundException,
    AppStorePrivateKeyMissingException,
    AppStoreRateLimitExceededException,
    AppStoreValidationException,
)
from app.schemas import ApplePayStoreCredentials
from app.services.cache.manager import cache_manager


@dataclass
class ApplePay:
    """
    Apple Pay Server API client wrapper.

    Handles verification and management of iOS In-App Purchases.
    Provides methods for transaction verification, subscription status,
    transaction history, refund history, and subscription renewal management.

    Follows the same pattern as Firebase service class with proper
    error handling and logging.
    """

    # Cache key patterns
    CACHE_PREFIX = "payments:applepay"
    SUBSCRIPTION_STATUS_KEY = f"{CACHE_PREFIX}:sub_status:{{user_id}}"
    TRANSACTION_INFO_KEY = f"{CACHE_PREFIX}:transaction:{{transaction_id}}"

    _client: AsyncAppStoreServerAPIClient | None = field(init=False, default=None)
    _credentials: ApplePayStoreCredentials | None = field(init=False, default=None)
    _environment: Environment = field(init=False, default=Environment.PRODUCTION)

    def __init__(
        self,
        credentials: ApplePayStoreCredentials | None = None,
    ) -> None:
        """
        Initialize Apple Pay service.

        Args:
            credentials: Apple Pay Connect API credentials
        """
        self.initialize_client(credentials=credentials)

    @property
    def client(self) -> AsyncAppStoreServerAPIClient:
        """
        Get the Apple Pay Server API client instance.

        Returns:
            AsyncAppStoreServerAPIClient: The Apple Pay API client

        Raises:
            AppStoreClientNotInitializedException: If client is not initialized
        """
        if self._client is None:
            raise AppStoreClientNotInitializedException("Apple Pay client not initialized")

        return self._client

    @property
    def credentials(self) -> ApplePayStoreCredentials:
        """
        Get the Apple Pay credentials.

        Returns:
            ApplePayStoreCredentials: The Apple Pay credentials

        Raises:
            AppStoreClientNotInitializedException: If credentials are not initialized
        """
        if self._credentials is None:
            raise AppStoreClientNotInitializedException("Apple Pay credentials not initialized")

        return self._credentials

    @property
    def current_environment(self) -> Environment:
        """
        Get the current Apple Pay environment.

        Returns:
            Environment: The Apple Pay environment (PRODUCTION or SANDBOX)
        """
        return self._environment

    def initialize_client(
        self,
        credentials: ApplePayStoreCredentials | None = None,
    ) -> None:
        """
        Initialize Apple Pay Server API client.

        The client is initialized with production environment by default.
        The library automatically handles sandbox receipts based on the
        transaction data.

        Args:
            credentials: Apple Pay Connect API credentials

        Raises:
            AppStorePrivateKeyMissingException: If credentials file not found
            AppStoreInvalidCredentialsException: If credentials are invalid
            AppStoreException: If client initialization fails
        """
        # Set credentials from parameter or settings
        self._credentials = credentials or settings.apple_pay_store_credentials
        sandbox_environments = {
            AppEnvironment.LOCAL,
            AppEnvironment.DEV,
            AppEnvironment.STG,
        }

        if settings.current_environment in sandbox_environments:
            self._environment = Environment.SANDBOX

        try:
            # Initialize the client with provided credentials
            # The library will auto-detect sandbox transactions
            self._client = AsyncAppStoreServerAPIClient(
                signing_key=self._credentials.private_key.encode("utf-8"),
                key_id=self._credentials.key_id,
                issuer_id=self._credentials.issuer_id,
                bundle_id=self._credentials.bundle_id,
                environment=self._environment,
            )
            logger.info("Apple Pay Server API client initialized successfully")
        except FileNotFoundError as err:
            logger.exception("Apple Pay private key file not found")
            raise AppStorePrivateKeyMissingException(
                "Apple Pay credentials file not found"
            ) from err
        except ValueError as err:
            logger.exception("Invalid Apple Pay credentials")
            raise AppStoreInvalidCredentialsException("Invalid Apple Pay credentials") from err
        except Exception as err:
            logger.exception("Unknown error initializing Apple Pay client")
            raise AppStoreException("Failed to initialize Apple Pay client") from err

    async def close_client(self) -> None:
        """
        Close the Apple Pay Server API client.

        Ensures that all resources are properly released.
        """
        if self._client is not None:
            await self._client.async_close()
            logger.info("Apple Pay Server API client closed successfully")

    async def check_connection(self) -> bool:
        """
        Check connection to Apple Pay Server API.

        Attempts to verify a dummy transaction to ensure connectivity
        and authentication with the Apple Pay servers.

        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            # Attempt to verify a non-existent transaction to test connection
            await self.verify_transaction(transaction_id="0000000000000000")
            return True
        except AppStoreNotFoundException:
            # Expected error for non-existent transaction, means connection is fine
            return True
        except AppStoreConnectionAbortedException:
            # Authentication failed, but connection is established
            return True
        except AppStoreConnectionErrorException:
            logger.exception("Apple Pay connection error")
            return False
        except Exception:
            logger.exception("Apple Pay connection check failed")
            return False

    def _validate_transaction_id(self, transaction_id: str) -> None:
        """
        Validate transaction ID format.

        Args:
            transaction_id: The transaction ID to validate

        Raises:
            AppStoreValidationException: If transaction_id is empty or invalid
        """
        if not transaction_id or not isinstance(transaction_id, str):
            logger.error("Transaction ID is empty or invalid")
            raise AppStoreValidationException("Transaction ID must be a non-empty string")

        if len(transaction_id.strip()) == 0:
            logger.error("Transaction ID is empty after stripping whitespace")
            raise AppStoreValidationException("Transaction ID cannot be empty or whitespace")

    async def verify_transaction(
        self,
        transaction_id: str,
    ) -> TransactionInfoResponse:
        """
        Verify a transaction by transaction ID.

        This is the primary method for purchase verification. It validates
        the transaction with Apple's servers and optionally checks if the
        product ID matches the expected value.

        Example:
            >>> apple_pay = ApplePay()
            >>> response = apple_pay.verify_transaction(
            ...     transaction_id="1000000123456789",
            ...     expected_product_id="com.superfit.subscription.monthly"
            ... )
            >>> print(response.signedTransactionInfo)

        Args:
            transaction_id: The transaction ID to verify

        Returns:
            TransactionInfoResponse: Transaction information response from Apple Pay

        Raises:
            AppStoreValidationException: If transaction_id is invalid or product_id doesn't match
            AppStoreNotFoundException: If transaction_id is not found
            AppStoreInvalidCredentialsException: If credentials are invalid
            AppStoreRateLimitExceededException: If rate limit exceeded
            AppStoreConnectionErrorException: If verification fails due to API error
            AppStoreConnectionAbortedException: If verification fails due to unexpected error
        """
        # Validate transaction ID format
        self._validate_transaction_id(transaction_id)

        try:
            logger.info(f"Verifying transaction: {transaction_id}")

            # Call Apple Pay API to get transaction info
            response: TransactionInfoResponse = await self.client.get_transaction_info(
                transaction_id
            )

            return response
        except ValueError as err:
            # Re-raise validation errors
            raise
        except APIException as err:
            # Handle Apple Pay API specific errors
            if err.http_status_code == 400:
                if transaction_id != "0000000000000000":
                    logger.error(f"Invalid transaction ID: {transaction_id}")

                logger.exception(f"APIException details: {err}")
                raise AppStoreNotFoundException(
                    f"Transaction ID {transaction_id} not found"
                ) from err
            elif err.http_status_code == 401:
                logger.exception(f"Apple Pay API authentication failed")
                raise AppStoreInvalidCredentialsException("Invalid Apple Pay credentials") from err
            elif err.http_status_code == 404:
                logger.exception(f"Transaction id {transaction_id} not found")
                raise AppStoreNotFoundException(
                    f"Transaction id {transaction_id} not found in Apple Pay"
                ) from err
            elif err.http_status_code == 429:
                logger.exception(f"Rate limit exceeded for transaction: {transaction_id}")
                raise AppStoreRateLimitExceededException(
                    "Apple Pay API rate limit exceeded"
                ) from err
            elif err.http_status_code == 500:
                logger.exception(f"Apple Pay API server error for transaction: {transaction_id}")
                raise AppStoreConnectionAbortedException("Apple Pay server error occurred") from err
            else:
                logger.exception(f"Apple Pay API error ({err.http_status_code}): {err}")
                raise AppStoreConnectionErrorException(
                    f"Failed to verify transaction: HTTP {err.http_status_code}"
                ) from err
        except Exception as err:
            logger.exception(f"Unexpected error verifying transaction {transaction_id}")
            raise AppStoreConnectionAbortedException(
                "Failed to verify transaction due to unexpected error"
            ) from err

    def check_product_id_in_transaction(
        self,
        transaction_info: JWSTransactionDecodedPayload,
        expected_product_id: str,
    ) -> None:
        """
        Check product ID in transaction info.

        Validates that the product ID in the transaction matches the expected
        product ID.

        Args:
            transaction_info: The decoded transaction information
            expected_product_id: The expected product ID to validate against

        Raises:
            AppStoreValidationException: If the product ID does not match
        """
        actual_product_id = transaction_info.productId
        if actual_product_id != expected_product_id:
            logger.error(
                f"Product ID mismatch. Expected: {expected_product_id}, "
                f"Got: {actual_product_id}"
            )
            raise AppStoreValidationException(
                f"Product ID mismatch. Expected '{expected_product_id}', "
                f"but transaction has '{actual_product_id}'"
            )

    async def get_transaction_history(
        self,
        original_transaction_id: str,
        revision: str | None = None,
    ) -> HistoryResponse:
        """
        Get transaction history for a subscription.

        Retrieves all transactions associated with a subscription, including
        renewals, upgrades, and downgrades. Useful for tracking subscription
        lifecycle and detecting renewal patterns.

        Example:
            >>> apple_pay = ApplePay()
            >>> history = apple_pay.get_transaction_history("1000000123456789")
            >>> for transaction in history.signedTransactions:
            ...     print(transaction)

        Args:
            original_transaction_id: The original transaction ID of the subscription
            revision: Optional revision token for pagination

        Returns:
            HistoryResponse: History response with all related transactions

        Raises:
            AppStoreNotFoundException: If transaction_id is not found
            AppStoreInvalidCredentialsException: If credentials are invalid
            AppStoreConnectionErrorException: If request fails
            AppStoreConnectionAbortedException: If subscription not found
        """
        # Validate transaction ID
        self._validate_transaction_id(original_transaction_id)

        try:
            logger.info(f"Fetching transaction history: {original_transaction_id}")

            # Create transaction history request
            history_request = TransactionHistoryRequest()

            # Call Apple Pay API to get transaction history
            response: HistoryResponse = await self.client.get_transaction_history(
                original_transaction_id,
                revision=revision,
                transaction_history_request=history_request,
            )
            logger.info(
                f"Transaction history retrieved: {original_transaction_id}, "
                f"Transactions count: {len(response.signedTransactions) if response.signedTransactions else 0}"
            )

            return response
        except APIException as err:
            if err.http_status_code == 404:
                logger.exception(f"Subscription not found: {original_transaction_id}")
                raise AppStoreConnectionAbortedException(
                    f"Subscription '{original_transaction_id}' not found"
                ) from err
            elif err.http_status_code == 401:
                logger.exception("Apple Pay API authentication failed")
                raise AppStoreInvalidCredentialsException("Invalid Apple Pay credentials") from err
            elif err.http_status_code == 500:
                logger.exception(
                    f"Apple Pay API server error for transaction: {original_transaction_id}"
                )
                raise AppStoreConnectionAbortedException("Apple Pay server error occurred") from err
            else:
                logger.exception(f"Apple Pay API error ({err.http_status_code}): {err}")
                raise AppStoreConnectionErrorException(
                    f"Failed to get transaction history: HTTP {err.http_status_code}"
                ) from err
        except Exception as err:
            logger.exception(f"Unexpected error fetching history for {original_transaction_id}")
            raise AppStoreConnectionAbortedException(
                "Failed to get transaction history due to unexpected error"
            ) from err

    async def get_subscription_status(
        self,
        original_transaction_id: str,
    ) -> StatusResponse:
        """
        Get current subscription status.

        Retrieves the current status of a subscription, including whether it's
        active, expired, or cancelled. Essential for checking if a user should
        have access to premium features.

        Example:
            >>> apple_pay = ApplePay()
            >>> status = apple_pay.get_subscription_status("1000000123456789")
            >>> for item in status.data:
            ...     print(f"Status: {item.lastTransactionsItem.status}")

        Args:
            original_transaction_id: The original transaction ID of the subscription

        Returns:
            StatusResponse: Subscription status response

        Raises:
            AppStoreNotFoundException: If transaction_id is not found
            AppStoreInvalidCredentialsException: If credentials are invalid
            AppStoreConnectionErrorException: If request fails
            AppStoreConnectionAbortedException: If subscription not found
        """
        # Validate transaction ID
        self._validate_transaction_id(original_transaction_id)

        try:
            logger.info(f"Fetching subscription status: {original_transaction_id}")
            # Call Apple Pay API to get subscription status
            response: StatusResponse = await self.client.get_all_subscription_statuses(
                original_transaction_id
            )
            logger.info(
                f"Subscription status retrieved: {original_transaction_id}, "
                f"Items count: {len(response.data) if response.data else 0}"
            )

            return response

        except APIException as err:
            if err.http_status_code == 404:
                logger.exception(f"Subscription not found: {original_transaction_id}")
                raise AppStoreConnectionAbortedException(
                    f"Subscription '{original_transaction_id}' not found"
                ) from err
            elif err.http_status_code == 401:
                logger.exception("Apple Pay API authentication failed")
                raise AppStoreInvalidCredentialsException("Invalid Apple Pay credentials") from err
            elif err.http_status_code == 500:
                logger.exception(
                    f"Apple Pay API server error for subscription: {original_transaction_id}"
                )
                raise AppStoreConnectionAbortedException("Apple Pay server error occurred") from err
            else:
                logger.exception(f"Apple Pay API error ({err.http_status_code}): {err}")
                raise AppStoreConnectionErrorException(
                    f"Failed to get subscription status: HTTP {err.http_status_code}"
                ) from err
        except Exception as err:
            logger.exception(
                f"Unexpected error fetching status for {original_transaction_id}: {err}"
            )
            raise AppStoreConnectionAbortedException(
                "Failed to get subscription status due to unexpected error"
            ) from err

    async def get_refund_history(
        self,
        original_transaction_id: str,
    ) -> RefundHistoryResponse:
        """
        Get refund history for a subscription.

        Retrieves all refunds associated with a subscription. Important for
        detecting refunded purchases and revoking access accordingly.

        Example:
            >>> apple_pay = ApplePay()
            >>> refunds = apple_pay.get_refund_history("1000000123456789")
            >>> for refund in refunds.signedTransactions:
            ...     print(f"Refunded: {refund}")

        Args:
            original_transaction_id: The original transaction ID of the subscription

        Returns:
            RefundHistoryResponse: Refund history response

        Raises:
            AppStoreInvalidCredentialsException: If credentials are invalid
            AppStoreConnectionErrorException: If request fails
            AppStoreConnectionAbortedException: If subscription not found
        """
        # Validate transaction ID
        self._validate_transaction_id(original_transaction_id)

        try:
            logger.info(f"Fetching refund history: {original_transaction_id}")

            # Call Apple Pay API to get refund history
            response: RefundHistoryResponse = await self.client.get_refund_history(
                original_transaction_id,
                revision=None,
            )

            logger.info(
                f"Refund history retrieved: {original_transaction_id}, "
                f"Refunds count: {len(response.signedTransactions) if response.signedTransactions else 0}"
            )

            return response

        except APIException as err:
            if err.http_status_code == 404:
                logger.exception(f"Subscription not found: {original_transaction_id}")
                raise AppStoreConnectionAbortedException(
                    f"Subscription '{original_transaction_id}' not found"
                ) from err
            elif err.http_status_code == 401:
                logger.exception("Apple Pay API authentication failed")
                raise AppStoreInvalidCredentialsException("Invalid Apple Pay credentials") from err
            elif err.http_status_code == 500:
                logger.exception(
                    f"Apple Pay API server error for transaction: {original_transaction_id}"
                )
                raise AppStoreConnectionAbortedException("Apple Pay server error occurred") from err
            else:
                logger.exception(f"Apple Pay API error ({err.http_status_code}): {err}")
                raise AppStoreConnectionErrorException(
                    f"Failed to get refund history: HTTP {err.http_status_code}"
                ) from err

        except Exception as err:
            logger.exception(
                f"Unexpected error fetching refund history for {original_transaction_id}: {err}"
            )
            raise AppStoreConnectionAbortedException(
                "Failed to get refund history due to unexpected error"
            ) from err

    async def extend_subscription_renewal_date(
        self,
        original_transaction_id: str,
        extend_by_days: int,
        extend_reason_code: ExtendReasonCode,
        request_identifier: str,
    ) -> ExtendRenewalDateResponse:
        """
        Extend a subscription's renewal date.

        Allows extending a subscription as a promotional gesture or for
        customer service purposes. Use cases include compensating for
        service outages or providing promotional extensions.

        Example:
            >>> import uuid
            >>> apple_pay = ApplePay()
            >>> response = apple_pay.extend_subscription_renewal_date(
            ...     original_transaction_id="1000000123456789",
            ...     extend_by_days=30,
            ...     extend_reason_code=1,  # Customer satisfaction
            ...     request_identifier=str(uuid.uuid4())
            ... )
            >>> print(f"New expiration: {response.effectiveDate}")

        Args:
            original_transaction_id: The original transaction ID of the subscription
            extend_by_days: Number of days to extend (max 90 days)
            extend_reason_code: Reason code (0=Undeclared, 1=CustomerSatisfaction, 2=Other)
            request_identifier: Unique identifier for this request (UUID recommended)

        Returns:
            ExtendRenewalDateResponse: Extension response

        Raises:
            AppStoreValidationException: If parameters are invalid
            AppStoreNotFoundException: if subscription is not found
            AppStoreInvalidCredentialsException: If credentials are invalid
            AppStoreConnectionAbortedException: If request fails
        """
        # Validate transaction ID
        self._validate_transaction_id(original_transaction_id)

        # Validate extend_by_days
        if not isinstance(extend_by_days, int) or extend_by_days < 1 or extend_by_days > 90:
            logger.error(f"Invalid extend_by_days: {extend_by_days}")
            raise AppStoreValidationException("extend_by_days must be an integer between 1 and 90")

        # Validate request_identifier
        if not request_identifier or not isinstance(request_identifier, str):
            logger.error("Invalid request_identifier")
            raise AppStoreValidationException("request_identifier must be a non-empty string")

        try:
            logger.info(
                f"Extending subscription renewal: {original_transaction_id}, "
                f"Days: {extend_by_days}, Reason: {extend_reason_code}"
            )

            # Create extend request
            extend_request = ExtendRenewalDateRequest(
                extendByDays=extend_by_days,
                extendReasonCode=extend_reason_code,
                requestIdentifier=request_identifier,
            )

            # Call Apple Pay API to extend renewal date
            response: ExtendRenewalDateResponse = (
                await self.client.extend_subscription_renewal_date(
                    original_transaction_id,
                    extend_request,
                )
            )

            logger.info(
                f"Subscription renewal extended: {original_transaction_id}, "
                f"Success: {response.success}"
            )

            return response

        except APIException as err:
            if err.http_status_code == 404:
                logger.exception(f"Subscription not found: {original_transaction_id}")
                raise AppStoreNotFoundException(
                    f"Subscription '{original_transaction_id}' not found"
                ) from err
            elif err.http_status_code == 401:
                logger.exception("Apple Pay API authentication failed")
                raise AppStoreInvalidCredentialsException("Invalid Apple Pay credentials") from err
            elif err.http_status_code == 400:
                logger.exception(f"Invalid extension request: {err}")
                raise AppStoreValidationException(f"Invalid extension request: {err}") from err
            elif err.http_status_code == 500:
                logger.exception(
                    f"Apple Pay API server error for transaction: {original_transaction_id}"
                )
                raise AppStoreConnectionAbortedException("Apple Pay server error occurred") from err
            else:
                logger.exception(f"Apple Pay API error ({err.http_status_code}): {err}")
                raise AppStoreConnectionAbortedException(
                    f"Failed to extend renewal date: HTTP {err.http_status_code}"
                ) from err

        except ValueError:
            # Re-raise validation errors
            raise

        except Exception as err:
            logger.exception(
                f"Unexpected error extending renewal for {original_transaction_id}: {err}"
            )
            raise AppStoreConnectionAbortedException(
                "Failed to extend renewal date due to unexpected error"
            ) from err

    async def decode_transaction_info(
        self,
        signed_transaction_info: TransactionInfoResponse,
    ) -> JWSTransactionDecodedPayload:
        """
        Decode signed transaction information.

        Utility method to decode signed transaction info using the
        SignedDataVerifier. Useful for extracting detailed transaction
        data after verification.

        Args:
            signed_transaction_info: The signed transaction info to decode

        Returns:
            JWSTransactionDecodedPayload: Decoded transaction information

        Raises:
            AppStoreValidationException: If decoding fails or signed data is invalid
            AppStoreConnectionAbortedException: If unexpected error occurs
        """
        try:
            verifier = SignedDataVerifier(
                root_certificates=[settings.apple_pay_store_root_certificate_path.read_bytes()],
                enable_online_checks=True,
                environment=self._environment,
                bundle_id=self.credentials.bundle_id,
                app_apple_id=None,
            )

            if signed_transaction_info.signedTransactionInfo is None:
                logger.error("Signed transaction info is missing")
                raise AppStoreValidationException("Invalid signed transaction info: missing data")

            transaction_info = verifier.verify_and_decode_signed_transaction(
                signed_transaction_info.signedTransactionInfo
            )
            logger.info("Transaction info decoded successfully")

            return transaction_info
        except Exception as err:
            logger.exception(f"Error decoding transaction info: {err}")
            raise AppStoreConnectionAbortedException("Failed to decode transaction info") from err

    async def verify_webhook_signature(
        self,
        signed_payload: str,
    ) -> ResponseBodyV2DecodedPayload:
        """
        Verify webhook notification signature from Apple.

        Uses SignedDataVerifier to cryptographically verify that the webhook
        payload was sent by Apple and hasn't been tampered with.

        Args:
            signed_payload: The signed JWT payload from webhook request

        Returns:
            Decoded notification data if signature is valid

        Raises:
            AppStoreValidationException: If signature is invalid or payload malformed
        """
        try:
            verifier = SignedDataVerifier(
                root_certificates=[settings.apple_pay_store_root_certificate_path.read_bytes()],
                enable_online_checks=True,
                environment=self._environment,
                bundle_id=self.credentials.bundle_id,
                app_apple_id=None,
            )

            # Verify and decode the signed notification
            notification = verifier.verify_and_decode_notification(signed_payload)
            logger.info(f"Webhook signature verified: {notification.notificationType}")

            return notification
        except Exception as err:
            logger.exception(f"Webhook signature verification failed: {err}")
            raise AppStoreValidationException("Invalid webhook signature") from err

    async def get_subscription_status_cached(
        self,
        user_id: int,
        original_transaction_id: str,
        force_refresh: bool = False,
    ) -> StatusResponse:
        """
        Get subscription status with caching to reduce API calls.

        Caches status for 10 minutes. Use force_refresh=True to bypass cache
        (e.g., after processing a webhook).

        Args:
            user_id: User ID for cache key
            original_transaction_id: Original transaction ID to check
            force_refresh: Skip cache and fetch fresh data from Apple

        Returns:
            StatusResponse from cache or Apple API

        Raises:
            Same exceptions as get_subscription_status()
        """
        cache_key = self.SUBSCRIPTION_STATUS_KEY.format(user_id=user_id)

        # Try cache first (unless force refresh)
        if not force_refresh:
            cached_status = await cache_manager.get(cache_key)
            if cached_status:
                logger.debug(f"Subscription status cache hit for user {user_id}")
                return cached_status

        # Cache miss - fetch from Apple
        logger.debug(f"Subscription status cache miss for user {user_id}")
        status = await self.get_subscription_status(original_transaction_id)

        # Cache for 10 minutes (600 seconds)
        await cache_manager.set(cache_key, status, expire=600)

        return status

    async def invalidate_subscription_cache(self, user_id: int) -> None:
        """
        Invalidate subscription cache for a user.

        Call this when subscription changes (e.g., from webhook notification).

        Args:
            user_id: User ID whose cache should be invalidated
        """
        cache_key = self.SUBSCRIPTION_STATUS_KEY.format(user_id=user_id)
        deleted = await cache_manager.delete(cache_key)
        if deleted:
            logger.info(f"Invalidated subscription cache for user {user_id}")
        else:
            logger.debug(f"No cache found for user {user_id}")

    def get_latest_transaction(
        self,
        history_response: HistoryResponse,
    ) -> JWSTransactionDecodedPayload | None:
        """
        Extract the most recent transaction from history.

        Useful for getting current subscription status from transaction history.

        Args:
            history_response: Response from get_transaction_history()

        Returns:
            Most recent decoded transaction, or None if no transactions
        """
        if not history_response.signedTransactions:
            logger.warning("No transactions in history response")
            return None

        try:
            verifier = SignedDataVerifier(
                root_certificates=[settings.apple_pay_store_root_certificate_path.read_bytes()],
                enable_online_checks=True,
                environment=self._environment,
                bundle_id=self.credentials.bundle_id,
                app_apple_id=None,
            )

            # Decode all transactions
            decoded_transactions = []
            for signed_tx in history_response.signedTransactions:
                decoded = verifier.verify_and_decode_signed_transaction(signed_tx)
                decoded_transactions.append(decoded)

            # Sort by purchase date (most recent first)
            decoded_transactions.sort(
                key=lambda tx: tx.purchaseDate or 0,
                reverse=True,
            )

            latest = decoded_transactions[0]
            logger.info(f"Latest transaction: {latest.transactionId}")
            return latest

        except Exception as err:
            logger.exception(f"Error extracting latest transaction")
            return None

    async def verify_and_process_subscription(
        self,
        transaction_id: str,
        expected_product_id: str | None = None,
    ) -> tuple[TransactionInfoResponse, JWSTransactionDecodedPayload]:
        """
        High-level method combining verification, decoding, and validation.

        Convenience method that performs all common verification steps:
        1. Verify transaction with Apple
        2. Decode the transaction info
        3. Optionally validate product ID

        Args:
            transaction_id: Transaction ID to verify
            expected_product_id: Optional product ID to validate

        Returns:
            Tuple of (raw response, decoded transaction info)

        Raises:
            All exceptions from verify_transaction() and decode_transaction_info()
        """
        # Verify transaction
        response = await self.verify_transaction(transaction_id)

        # Decode transaction info
        transaction_info = await self.decode_transaction_info(response)

        # Validate product ID if provided
        if expected_product_id:
            self.check_product_id_in_transaction(transaction_info, expected_product_id)

        return response, transaction_info


apple_pay = ApplePay()
