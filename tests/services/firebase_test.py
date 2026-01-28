from unittest.mock import AsyncMock, Mock, patch

import pytest
from faker import Faker
from firebase_admin import App
from firebase_admin.auth import (
    ExpiredIdTokenError,
    InvalidIdTokenError,
    RevokedIdTokenError,
    UserNotFoundError,
)
from firebase_admin.exceptions import FirebaseError
from firebase_admin.messaging import BatchResponse, SendResponse

from app.schemas import FirebaseServiceAccount
from app.services.firebase import Firebase


class TestFirebaseInitialization:
    """Test Firebase initialization."""

    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    def test_init_new_app(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        mock_firebase_app: Mock,
    ):
        """Test Firebase initialization when app doesn't exist."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = mock_firebase_app

        firebase = Firebase(firebase_service_account)

        assert firebase._default_app == mock_firebase_app
        mock_cert.assert_called_once()
        mock_init_app.assert_called_once()

    @patch("app.services.firebase.firebase_admin.get_app")
    def test_init_existing_app(
        self, mock_get_app: Mock, firebase_service_account: FirebaseServiceAccount
    ):
        """Test Firebase initialization when app already exists."""
        mock_get_app.return_value = Mock(spec=App)

        Firebase(firebase_service_account)

        mock_get_app.assert_called_once()

    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.credentials.Certificate")
    def test_init_io_error(
        self,
        mock_cert: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test Firebase initialization with IOError."""
        mock_get_app.side_effect = ValueError("No app")
        mock_cert.side_effect = IOError("Certificate file not found")

        with pytest.raises(IOError):
            Firebase(firebase_service_account)

    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    def test_init_value_error(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test Firebase initialization with ValueError during init."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.side_effect = ValueError("Init failed")

        with pytest.raises(ValueError):
            Firebase(firebase_service_account)

    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    def test_init_generic_exception(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test Firebase initialization with generic exception."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.side_effect = Exception("Unknown error")

        with pytest.raises(Exception):
            Firebase(firebase_service_account)

    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    def test_app_property_success(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        mock_firebase_app: Mock,
    ):
        """Test app property returns app."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = mock_firebase_app

        firebase = Firebase(firebase_service_account)
        assert firebase.app == mock_firebase_app

    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.credentials.Certificate")
    def test_app_property_none(
        self, mock_cert: Mock, mock_get_app: Mock, firebase_service_account: FirebaseServiceAccount
    ):
        """Test app property when app is None."""
        mock_get_app.side_effect = ValueError("No app")
        mock_cert.side_effect = IOError("File not found")

        try:
            firebase = Firebase(firebase_service_account)
        except IOError:
            pass

        firebase = Firebase.__new__(Firebase)
        firebase._default_app = None

        with pytest.raises(ValueError) as exc_info:
            _ = firebase.app

        assert "Firebase app not initialized" in str(exc_info.value)


class TestFirebaseUserOperations:
    """Test Firebase user operations."""

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    @patch("app.services.firebase.auth.get_user")
    async def test_get_user_by_id_success(
        self,
        mock_get_user: Mock,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        mock_user_record: Mock,
        faker_instance: Faker,
    ):
        """Test successful get_user_by_id."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = mock_user_record
            result = await firebase.get_user_by_id(faker_instance.uuid4())

            assert result == mock_user_record

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_get_user_by_id_malformed(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test get_user_by_id with malformed ID."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = ValueError("Malformed ID")

            with pytest.raises(ValueError):
                await firebase.get_user_by_id("invalid_id")

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_get_user_by_id_not_found(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test get_user_by_id when user not found."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = UserNotFoundError("User not found")

            with pytest.raises(ConnectionAbortedError) as exc_info:
                await firebase.get_user_by_id(faker_instance.uuid4())

            assert "User not found" in str(exc_info.value)

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_get_user_by_id_firebase_error(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test get_user_by_id with Firebase error."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = FirebaseError("code", "Firebase error")

            with pytest.raises(ConnectionError):
                await firebase.get_user_by_id(faker_instance.uuid4())

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_get_user_by_email_success(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        mock_user_record: Mock,
        faker_instance: Faker,
    ):
        """Test successful get_user_by_email."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = mock_user_record
            result = await firebase.get_user_by_email(faker_instance.email())

            assert result == mock_user_record

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_get_user_by_email_malformed(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test get_user_by_email with malformed email."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = ValueError("Malformed email")

            with pytest.raises(ValueError):
                await firebase.get_user_by_email("invalid_email")

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_get_user_by_email_not_found(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test get_user_by_email when user not found."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = UserNotFoundError("User not found")

            with pytest.raises(ConnectionAbortedError):
                await firebase.get_user_by_email(faker_instance.email())

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_get_user_by_email_firebase_error(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test get_user_by_email with Firebase error."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = FirebaseError("code", "Firebase error")

            with pytest.raises(ConnectionError):
                await firebase.get_user_by_email(faker_instance.email())

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_get_user_by_phone_number_success(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        mock_user_record: Mock,
        faker_instance: Faker,
    ):
        """Test successful get_user_by_phone_number."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = mock_user_record
            result = await firebase.get_user_by_phone_number(faker_instance.phone_number())

            assert result == mock_user_record

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_get_user_by_phone_number_malformed(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test get_user_by_phone_number with malformed phone."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = ValueError("Malformed phone")

            with pytest.raises(ValueError):
                await firebase.get_user_by_phone_number("invalid")

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_get_user_by_phone_number_not_found(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test get_user_by_phone_number when user not found."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = UserNotFoundError("User not found")

            with pytest.raises(ConnectionAbortedError):
                await firebase.get_user_by_phone_number(faker_instance.phone_number())

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_get_user_by_phone_number_firebase_error(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test get_user_by_phone_number with Firebase error."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = FirebaseError("code", "Firebase error")

            with pytest.raises(ConnectionError):
                await firebase.get_user_by_phone_number(faker_instance.phone_number())

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_get_all_users_success(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        mock_list_users_page: Mock,
    ):
        """Test successful get_all_users."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = mock_list_users_page
            result = await firebase.get_all_users()

            assert result == mock_list_users_page

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_get_all_users_with_custom_max(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        mock_list_users_page: Mock,
    ):
        """Test get_all_users with custom max_results."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = mock_list_users_page
            result = await firebase.get_all_users(max_results=500)

            assert result == mock_list_users_page

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_get_all_users_value_error(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test get_all_users with ValueError."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = ValueError("Invalid max_results")

            with pytest.raises(ValueError):
                await firebase.get_all_users(max_results=-1)

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_get_all_users_firebase_error(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test get_all_users with Firebase error."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = FirebaseError("code", "Firebase error")

            with pytest.raises(ConnectionError):
                await firebase.get_all_users()


class TestFirebaseTokenOperations:
    """Test Firebase token operations."""

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_create_custom_id_token_success(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test successful custom ID token creation."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = b"custom_token"
            result = await firebase.create_custom_id_token(faker_instance.uuid4())

            assert result == b"custom_token"

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_create_custom_id_token_with_claims(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test custom ID token creation with additional claims."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = b"custom_token"
            result = await firebase.create_custom_id_token(
                faker_instance.uuid4(), additional_claims={"role": "admin"}
            )

            assert result == b"custom_token"

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_create_custom_id_token_value_error(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test create_custom_id_token with malformed UID."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = ValueError("Malformed UID")

            with pytest.raises(ValueError):
                await firebase.create_custom_id_token("invalid")

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_create_custom_id_token_firebase_error(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test create_custom_id_token with Firebase error."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = FirebaseError("code", "Firebase error")

            with pytest.raises(ConnectionError):
                await firebase.create_custom_id_token(faker_instance.uuid4())

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_verify_id_token_success(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test successful ID token verification."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = {
                "uid": faker_instance.uuid4(),
                "email": faker_instance.email(),
            }
            result = await firebase.verify_id_token("valid_token")

            assert result.uid is not None
            assert result.email is not None

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_verify_id_token_malformed(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test verify_id_token with malformed token."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = ValueError("Malformed token")

            with pytest.raises(ValueError):
                await firebase.verify_id_token("invalid")

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    @patch("app.services.firebase.auth.RevokedIdTokenError", RevokedIdTokenError)
    async def test_verify_id_token_revoked(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test verify_id_token with revoked token."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = RevokedIdTokenError("Token revoked")

            with pytest.raises(ConnectionAbortedError) as exc_info:
                await firebase.verify_id_token("revoked_token")

            assert "revoked" in str(exc_info.value)

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    @patch("app.services.firebase.auth.ExpiredIdTokenError", ExpiredIdTokenError)
    async def test_verify_id_token_expired(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test verify_id_token with expired token."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = ExpiredIdTokenError("Token expired", "cause")

            with pytest.raises(ConnectionAbortedError) as exc_info:
                await firebase.verify_id_token("expired_token")

            assert "expired" in str(exc_info.value)

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    @patch("app.services.firebase.auth.InvalidIdTokenError", InvalidIdTokenError)
    async def test_verify_id_token_invalid(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test verify_id_token with invalid token."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = InvalidIdTokenError("Invalid token")

            with pytest.raises(ConnectionAbortedError) as exc_info:
                await firebase.verify_id_token("invalid_token")

            assert "Invalid" in str(exc_info.value)

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_verify_id_token_firebase_error(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test verify_id_token with Firebase error."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = FirebaseError("code", "Firebase error")

            with pytest.raises(ConnectionError):
                await firebase.verify_id_token("token")


class TestFirebaseMessaging:
    """Test Firebase Cloud Messaging operations."""

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_validate_fcm_token_success(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test successful FCM token validation."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = "message_id"
            result = await firebase.validate_fcm_token(faker_instance.uuid4())

            assert result is True

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_validate_fcm_token_firebase_error(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test validate_fcm_token with Firebase error."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = FirebaseError("code", "Invalid token")
            result = await firebase.validate_fcm_token(faker_instance.uuid4())

            assert result is False

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_validate_fcm_token_value_error(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test validate_fcm_token with malformed token."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = ValueError("Malformed")
            result = await firebase.validate_fcm_token("invalid")

            assert result is False

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_validate_fcm_token_generic_exception(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test validate_fcm_token with generic exception."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = Exception("Unknown error")
            result = await firebase.validate_fcm_token(faker_instance.uuid4())

            assert result is False

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_notify_a_device_success(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test successful device notification."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = "message_id_123"
            result = await firebase.notify_a_device(
                faker_instance.uuid4(), "Test Title", "Test Content"
            )

            assert result is True

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_notify_a_device_failure(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test device notification failure."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = Exception("Send failed")
            result = await firebase.notify_a_device(
                faker_instance.uuid4(), "Test Title", "Test Content"
            )

            assert result is False

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_notify_multiple_devices_success(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        mock_batch_response: Mock,
        faker_instance: Faker,
    ):
        """Test successful multiple device notification."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        tokens = [faker_instance.uuid4() for _ in range(10)]

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = mock_batch_response
            result = await firebase.notify_multiple_devices(tokens, "Title", "Content")

            assert result == 5

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_notify_multiple_devices_with_failures(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test multiple device notification with some failures."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        # Create batch response with failures
        mock_response = Mock(spec=BatchResponse)
        mock_response.success_count = 3
        mock_response.failure_count = 2

        failed_response = Mock(spec=SendResponse)
        failed_response.success = False
        failed_response.message_id = None
        failed_response.exception = Exception("Failed to send")

        mock_response.responses = [
            Mock(spec=SendResponse, success=True),
            Mock(spec=SendResponse, success=True),
            Mock(spec=SendResponse, success=True),
            failed_response,
            failed_response,
        ]

        tokens = [faker_instance.uuid4() for _ in range(5)]

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = mock_response
            result = await firebase.notify_multiple_devices(tokens, "Title", "Content")

            assert result == 3

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_notify_multiple_devices_firebase_error(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test multiple device notification with Firebase error."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        tokens = [faker_instance.uuid4() for _ in range(5)]

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = FirebaseError("code", "Send failed")
            result = await firebase.notify_multiple_devices(tokens, "Title", "Content")

            assert result == 0

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_notify_multiple_devices_value_error(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test multiple device notification with ValueError."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        tokens = [faker_instance.uuid4() for _ in range(5)]

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = ValueError("Invalid params")
            result = await firebase.notify_multiple_devices(tokens, "Title", "Content")

            assert result == 0

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_notify_multiple_devices_generic_exception(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test multiple device notification with generic exception."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        tokens = [faker_instance.uuid4() for _ in range(5)]

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = Exception("Unknown error")
            result = await firebase.notify_multiple_devices(tokens, "Title", "Content")

            assert result == 0

    @pytest.mark.anyio
    @patch("app.services.firebase.firebase_admin.get_app")
    @patch("app.services.firebase.firebase_admin.initialize_app")
    @patch("app.services.firebase.credentials.Certificate")
    async def test_notify_multiple_devices_large_batch(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        mock_batch_response: Mock,
        faker_instance: Faker,
    ):
        """Test multiple device notification with large batch (>500 tokens)."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = Mock(spec=App)

        firebase = Firebase(firebase_service_account)

        # Create 750 tokens to test chunking
        tokens = [faker_instance.uuid4() for _ in range(750)]

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = mock_batch_response
            result = await firebase.notify_multiple_devices(tokens, "Title", "Content")

            # Should be called twice (500 + 250)
            assert mock_to_thread.call_count == 2
            # Total success count from 2 batches
            assert result == 10
