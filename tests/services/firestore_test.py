from unittest.mock import AsyncMock, Mock, patch

import pytest
from faker import Faker
from firebase_admin import App
from google.cloud.exceptions import NotFound

from app.core.exceptions.firebase_exceptions import FirebaseDocumentNotFoundError
from app.schemas import FirebaseServiceAccount
from app.services.firestore import Firestore


class TestFirestoreInitialization:
    """Test Firestore initialization."""

    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firestore_async.client")
    def test_init_existing_app(
        self,
        mock_firestore_client: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test Firestore initialization when app exists."""
        mock_app = Mock(spec=App)
        mock_get_app.return_value = mock_app
        mock_firestore_client.return_value = Mock()

        firestore = Firestore(firebase_service_account)

        assert firestore._firestore_client is not None
        mock_get_app.assert_called_once()

    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firebase_admin.initialize_app")
    @patch("app.services.firestore.firestore_async.client")
    @patch("app.services.firestore.credentials.Certificate")
    def test_init_new_app(
        self,
        mock_cert: Mock,
        mock_firestore_client: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        mock_firebase_app: Mock,
    ):
        """Test Firestore initialization creating new app."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.return_value = mock_firebase_app
        mock_firestore_client.return_value = Mock()

        firestore = Firestore(firebase_service_account)

        assert firestore._default_app == mock_firebase_app
        assert firestore._firestore_client is not None

    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.credentials.Certificate")
    def test_init_io_error(
        self,
        mock_cert: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test Firestore initialization with IOError."""
        mock_get_app.side_effect = ValueError("No app")
        mock_cert.side_effect = IOError("Certificate file not found")

        with pytest.raises(IOError):
            Firestore(firebase_service_account)

    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firebase_admin.initialize_app")
    @patch("app.services.firestore.credentials.Certificate")
    def test_init_value_error(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test Firestore initialization with ValueError."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.side_effect = ValueError("Init failed")

        with pytest.raises(ValueError):
            Firestore(firebase_service_account)

    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firebase_admin.initialize_app")
    @patch("app.services.firestore.credentials.Certificate")
    def test_init_generic_exception(
        self,
        mock_cert: Mock,
        mock_init_app: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test Firestore initialization with generic exception."""
        mock_get_app.side_effect = ValueError("No app")
        mock_init_app.side_effect = Exception("Unknown error")

        with pytest.raises(Exception):
            Firestore(firebase_service_account)

    @patch("app.services.firestore.credentials.Certificate")
    @patch("app.services.firestore.firebase_admin.initialize_app")
    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firestore_async.client")
    def test_app_property_success(
        self,
        mock_firestore_client: Mock,
        mock_get_app: Mock,
        mock_initialize_app: Mock,
        mock_certificate: Mock,
        firebase_service_account: FirebaseServiceAccount,
        mock_firebase_app: Mock,
    ):
        """Test app property returns app."""
        mock_get_app.side_effect = ValueError()  # App doesn't exist initially
        mock_certificate.return_value = Mock()
        mock_initialize_app.return_value = mock_firebase_app
        mock_firestore_client.return_value = Mock()

        firestore = Firestore(firebase_service_account)
        assert firestore.app == mock_firebase_app

    def test_app_property_none(self):
        """Test app property when app is None."""
        firestore = Firestore.__new__(Firestore)
        firestore._default_app = None

        with pytest.raises(ValueError) as exc_info:
            _ = firestore.app

        assert "Firebase app not initialized" in str(exc_info.value)

    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firestore_async.client")
    def test_firestore_client_property_success(
        self,
        mock_firestore_client_func: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        mock_firestore_client: Mock,
    ):
        """Test firestore_client property returns client."""
        mock_get_app.return_value = Mock(spec=App)
        mock_firestore_client_func.return_value = mock_firestore_client

        firestore = Firestore(firebase_service_account)
        assert firestore.firestore_client == mock_firestore_client

    def test_firestore_client_property_none(self):
        """Test firestore_client property when client is None."""
        firestore = Firestore.__new__(Firestore)
        firestore._firestore_client = None

        with pytest.raises(ValueError) as exc_info:
            _ = firestore.firestore_client

        assert "Firestore client not initialized" in str(exc_info.value)


class TestFirestoreDocumentOperations:
    """Test Firestore document operations."""

    @pytest.mark.anyio
    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firestore_async.client")
    async def test_fetch_all_documents_success(
        self,
        mock_firestore_client_func: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test successful fetch_all_documents."""
        mock_get_app.return_value = Mock(spec=App)
        mock_client = Mock()
        mock_firestore_client_func.return_value = mock_client

        # Create mock documents
        mock_doc1 = Mock()
        mock_doc1.to_dict = Mock(return_value={"id": "1", "name": "Doc1"})
        mock_doc2 = Mock()
        mock_doc2.to_dict = Mock(return_value={"id": "2", "name": "Doc2"})

        async def mock_stream():
            yield mock_doc1
            yield mock_doc2

        mock_collection = Mock()
        mock_collection.stream = Mock(return_value=mock_stream())
        mock_client.collection = Mock(return_value=mock_collection)

        firestore = Firestore(firebase_service_account)
        result = await firestore.fetch_all_documents("test_collection")

        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "2"

    @pytest.mark.anyio
    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firestore_async.client")
    async def test_fetch_all_documents_with_none(
        self,
        mock_firestore_client_func: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test fetch_all_documents filtering None documents."""
        mock_get_app.return_value = Mock(spec=App)
        mock_client = Mock()
        mock_firestore_client_func.return_value = mock_client

        mock_doc1 = Mock()
        mock_doc1.to_dict = Mock(return_value={"id": "1"})
        mock_doc2 = Mock()
        mock_doc2.to_dict = Mock(return_value=None)

        async def mock_stream():
            yield mock_doc1
            yield mock_doc2

        mock_collection = Mock()
        mock_collection.stream = Mock(return_value=mock_stream())
        mock_client.collection = Mock(return_value=mock_collection)

        firestore = Firestore(firebase_service_account)
        result = await firestore.fetch_all_documents("test_collection")

        assert len(result) == 1

    @pytest.mark.anyio
    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firestore_async.client")
    async def test_fetch_all_documents_failure(
        self,
        mock_firestore_client_func: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test fetch_all_documents with exception."""
        mock_get_app.return_value = Mock(spec=App)
        mock_client = Mock()
        mock_firestore_client_func.return_value = mock_client

        mock_client.collection = Mock(side_effect=Exception("Fetch failed"))

        firestore = Firestore(firebase_service_account)

        with pytest.raises(Exception) as exc_info:
            await firestore.fetch_all_documents("test_collection")

        assert "Fetch failed" in str(exc_info.value)

    @pytest.mark.anyio
    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firestore_async.client")
    async def test_add_document_success(
        self,
        mock_firestore_client_func: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
        faker_instance: Faker,
    ):
        """Test successful add_document."""
        mock_get_app.return_value = Mock(spec=App)
        mock_client = Mock()
        mock_firestore_client_func.return_value = mock_client

        mock_doc_ref = Mock()
        mock_doc_ref.set = AsyncMock()

        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_client.collection = Mock(return_value=mock_collection)

        firestore = Firestore(firebase_service_account)
        await firestore.add_document("test_collection", "doc_id", {"name": "Test"})

        mock_doc_ref.set.assert_called_once_with({"name": "Test"})

    @pytest.mark.anyio
    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firestore_async.client")
    async def test_add_document_failure(
        self,
        mock_firestore_client_func: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test add_document with exception."""
        mock_get_app.return_value = Mock(spec=App)
        mock_client = Mock()
        mock_firestore_client_func.return_value = mock_client

        mock_doc_ref = Mock()
        mock_doc_ref.set = AsyncMock(side_effect=Exception("Add failed"))

        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_client.collection = Mock(return_value=mock_collection)

        firestore = Firestore(firebase_service_account)

        with pytest.raises(Exception) as exc_info:
            await firestore.add_document("test_collection", "doc_id", {"name": "Test"})

        assert "Add failed" in str(exc_info.value)

    @pytest.mark.anyio
    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firestore_async.client")
    async def test_update_document_success(
        self,
        mock_firestore_client_func: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test successful update_document."""
        mock_get_app.return_value = Mock(spec=App)
        mock_client = Mock()
        mock_firestore_client_func.return_value = mock_client

        mock_doc_ref = Mock()
        mock_doc_ref.update = AsyncMock()

        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_client.collection = Mock(return_value=mock_collection)

        firestore = Firestore(firebase_service_account)
        await firestore.update_document("test_collection", "doc_id", {"name": "Updated"})

        mock_doc_ref.update.assert_called_once_with({"name": "Updated"})

    @pytest.mark.anyio
    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firestore_async.client")
    async def test_update_document_not_found(
        self,
        mock_firestore_client_func: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test update_document with NotFound exception."""
        mock_get_app.return_value = Mock(spec=App)
        mock_client = Mock()
        mock_firestore_client_func.return_value = mock_client

        mock_doc_ref = Mock()
        mock_doc_ref.update = AsyncMock(side_effect=NotFound("Document not found"))

        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_client.collection = Mock(return_value=mock_collection)

        firestore = Firestore(firebase_service_account)

        with pytest.raises(FirebaseDocumentNotFoundError) as exc_info:
            await firestore.update_document("test_collection", "doc_id", {"name": "Updated"})

        assert "not found" in str(exc_info.value)

    @pytest.mark.anyio
    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firestore_async.client")
    async def test_update_document_other_exception(
        self,
        mock_firestore_client_func: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test update_document with other exception."""
        mock_get_app.return_value = Mock(spec=App)
        mock_client = Mock()
        mock_firestore_client_func.return_value = mock_client

        mock_doc_ref = Mock()
        mock_doc_ref.update = AsyncMock(side_effect=Exception("Update failed"))

        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_client.collection = Mock(return_value=mock_collection)

        firestore = Firestore(firebase_service_account)

        with pytest.raises(Exception) as exc_info:
            await firestore.update_document("test_collection", "doc_id", {"name": "Updated"})

        assert "Update failed" in str(exc_info.value)

    @pytest.mark.anyio
    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firestore_async.client")
    async def test_remove_document_success(
        self,
        mock_firestore_client_func: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test successful remove_document."""
        mock_get_app.return_value = Mock(spec=App)
        mock_client = Mock()
        mock_firestore_client_func.return_value = mock_client

        mock_doc_ref = Mock()
        mock_doc_ref.delete = AsyncMock()

        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_client.collection = Mock(return_value=mock_collection)

        firestore = Firestore(firebase_service_account)
        await firestore.remove_document("test_collection", "doc_id")

        mock_doc_ref.delete.assert_called_once()

    @pytest.mark.anyio
    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firestore_async.client")
    async def test_remove_document_failure(
        self,
        mock_firestore_client_func: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test remove_document with exception."""
        mock_get_app.return_value = Mock(spec=App)
        mock_client = Mock()
        mock_firestore_client_func.return_value = mock_client

        mock_doc_ref = Mock()
        mock_doc_ref.delete = AsyncMock(side_effect=Exception("Delete failed"))

        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_client.collection = Mock(return_value=mock_collection)

        firestore = Firestore(firebase_service_account)

        with pytest.raises(Exception) as exc_info:
            await firestore.remove_document("test_collection", "doc_id")

        assert "Delete failed" in str(exc_info.value)

    @pytest.mark.anyio
    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firestore_async.client")
    async def test_get_document_exists(
        self,
        mock_firestore_client_func: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test get_document when document exists."""
        mock_get_app.return_value = Mock(spec=App)
        mock_client = Mock()
        mock_firestore_client_func.return_value = mock_client

        mock_snapshot = Mock()
        mock_snapshot.exists = True
        mock_snapshot.to_dict = Mock(return_value={"id": "1", "name": "Test"})

        mock_doc_ref = Mock()
        mock_doc_ref.get = AsyncMock(return_value=mock_snapshot)

        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_client.collection = Mock(return_value=mock_collection)

        firestore = Firestore(firebase_service_account)
        result = await firestore.get_document("test_collection", "doc_id")

        assert result is not None
        assert result["id"] == "1"
        assert result["name"] == "Test"

    @pytest.mark.anyio
    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firestore_async.client")
    async def test_get_document_not_exists(
        self,
        mock_firestore_client_func: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test get_document when document doesn't exist."""
        mock_get_app.return_value = Mock(spec=App)
        mock_client = Mock()
        mock_firestore_client_func.return_value = mock_client

        mock_snapshot = Mock()
        mock_snapshot.exists = False

        mock_doc_ref = Mock()
        mock_doc_ref.get = AsyncMock(return_value=mock_snapshot)

        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_client.collection = Mock(return_value=mock_collection)

        firestore = Firestore(firebase_service_account)
        result = await firestore.get_document("test_collection", "doc_id")

        assert result is None

    @pytest.mark.anyio
    @patch("app.services.firestore.firebase_admin.get_app")
    @patch("app.services.firestore.firestore_async.client")
    async def test_get_document_failure(
        self,
        mock_firestore_client_func: Mock,
        mock_get_app: Mock,
        firebase_service_account: FirebaseServiceAccount,
    ):
        """Test get_document with exception."""
        mock_get_app.return_value = Mock(spec=App)
        mock_client = Mock()
        mock_firestore_client_func.return_value = mock_client

        mock_doc_ref = Mock()
        mock_doc_ref.get = AsyncMock(side_effect=Exception("Get failed"))

        mock_collection = Mock()
        mock_collection.document = Mock(return_value=mock_doc_ref)
        mock_client.collection = Mock(return_value=mock_collection)

        firestore = Firestore(firebase_service_account)

        with pytest.raises(Exception) as exc_info:
            await firestore.get_document("test_collection", "doc_id")

        assert "Get failed" in str(exc_info.value)
