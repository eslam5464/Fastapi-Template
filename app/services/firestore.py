from dataclasses import dataclass, field
from typing import Any

import firebase_admin
from firebase_admin import App, credentials, firestore_async
from firebase_admin.credentials import Certificate
from google.cloud.exceptions import NotFound
from google.cloud.firestore import AsyncClient
from loguru import logger

from app.core.exceptions.firebase_exceptions import (
    FirebaseDocumentNotFoundError,
)
from app.schemas import FirebaseServiceAccount


@dataclass
class Firestore:
    _default_app: App | None = field(init=False, default=None)
    _app_certificate: Certificate | None = field(init=False, default=None)
    _firestore_client: AsyncClient | None = field(init=False, default=None)

    def __init__(self, service_account: FirebaseServiceAccount):
        """
        Initialize the Firestore class

        Args:
            service_account (FirebaseServiceAccount): Firebase service account credentials

        Raises:
            IOError: If the service account file is not found
            ValueError: If there is an error initializing the Firebase app
            Exception: For any other errors during initialization
        """
        try:
            firebase_admin.get_app()
            self._firestore_client = firestore_async.client(self._default_app)
            app_exists = True
        except ValueError:
            app_exists = False

        try:
            if not app_exists:
                self._app_certificate = credentials.Certificate(service_account.model_dump())
                self._default_app = firebase_admin.initialize_app(
                    credential=self._app_certificate,
                )
                self._firestore_client = firestore_async.client(self._default_app)
        except IOError as err:
            logger.exception(
                "Error initializing Firestore app, certificate file not found",
            )
            raise err
        except ValueError as err:
            logger.exception("Error initializing Firestore app")
            raise err
        except Exception as ex:
            logger.exception(
                "Error initializing Firestore app, unknown error",
            )
            raise ex

    @property
    def app(self) -> App:
        """
        Get the default Firebase app

        Returns:
            app: The default Firebase app

        Raises:
            ValueError: If the default Firebase app is not initialized
        """
        if self._default_app is None:
            logger.error("Firebase app not initialized")
            raise ValueError("Firebase app not initialized")

        return self._default_app

    @property
    def firestore_client(self) -> AsyncClient:
        """
        Get the Firestore client

        Returns:
            firestore_client: The Firestore client

        Raises:
            ValueError: If the Firestore client is not initialized
        """
        if self._firestore_client is None:
            logger.error("Firestore client not initialized")
            raise ValueError("Firestore client not initialized")

        return self._firestore_client

    async def fetch_all_documents(self, collection_name: str) -> list[dict[str, Any]]:
        """
        Fetch all documents from a collection

        Args:
            collection_name (str): Name of the collection to fetch documents from

        Returns:
            documents: List of documents in the collection
        """
        try:
            collection_ref = self.firestore_client.collection(collection_name)
            docs = collection_ref.stream()
            return [doc_dict async for doc in docs if (doc_dict := doc.to_dict()) is not None]
        except Exception as ex:
            logger.exception("Error fetching documents from collection")
            raise ex

    async def add_document(self, collection_name: str, document_id: str, data: dict) -> None:
        """
        Add a document to a collection

        Args:
            collection_name (str): Name of the collection
            document_id (str): ID of the document
            data (dict): Data to add to the document

        Raises:
            Exception: If there is an error adding the document
        """
        try:
            doc_ref = self.firestore_client.collection(collection_name).document(document_id)
            await doc_ref.set(data)
            logger.debug(f"Document added to collection {collection_name} with ID {document_id}")
        except Exception as ex:
            logger.exception("Error adding document to collection")
            raise ex

    async def update_document(self, collection_name: str, document_id: str, data: dict) -> None:
        """
        Update a document in a collection

        Args:
            collection_name (str): Name of the collection
            document_id (str): ID of the document
            data (dict): Data to update in the document

        Raises:
            FirebaseDocumentNotFoundError: If the document does not exist
            Exception: If there is an error updating the document
        """
        try:
            doc_ref = self.firestore_client.collection(collection_name).document(document_id)
            await doc_ref.update(data)
            logger.debug(f"Document updated in collection {collection_name} with ID {document_id}")
        except NotFound as ex:
            logger.exception(
                f"Document with ID {document_id} not found in collection {collection_name}"
            )
            raise FirebaseDocumentNotFoundError(
                f"Document with ID {document_id} not found in collection {collection_name}"
            ) from ex
        except Exception as ex:
            logger.exception(f"Error updating document in collection {collection_name}")
            raise ex

    async def remove_document(self, collection_name: str, document_id: str) -> None:
        """
        Remove a document from a collection

        Args:
            collection_name (str): Name of the collection
            document_id (str): ID of the document to remove

        Raises:
            Exception: If there is an error removing the document
        """
        try:
            doc_ref = self.firestore_client.collection(collection_name).document(document_id)
            await doc_ref.delete()
            logger.debug(
                f"Document removed from collection {collection_name} with ID {document_id}"
            )
        except Exception as ex:
            logger.exception(
                f"Error removing document from collection {collection_name} with ID {document_id}"
            )
            raise ex

    async def get_document(self, collection_name: str, document_id: str) -> dict[str, Any] | None:
        """
        Get a document from a collection

        Args:
            collection_name (str): Name of the collection
            document_id (str): ID of the document to get

        Returns:
            document: The document data if found, else None

        Raises:
            Exception: If there is an error getting the document
        """
        try:
            doc_ref = self.firestore_client.collection(collection_name).document(document_id)
            doc = await doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            else:
                return None
        except Exception as ex:
            logger.exception(f"Error getting document from collection {collection_name}")
            raise ex
