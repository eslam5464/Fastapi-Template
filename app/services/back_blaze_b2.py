import os
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Self

from b2sdk._internal.bucket import Bucket
from b2sdk._internal.file_version import FileVersion
from b2sdk.v2 import B2Api, B2RawHTTPApi, FileIdAndName
from b2sdk.v2.b2http import B2Http
from b2sdk.v2.exception import NonExistentBucket
from loguru import logger
from pydantic import AnyUrl

from app.core.exceptions.back_blaze_exceptions import (
    B2AuthorizationError,
    B2BucketNotFoundError,
    B2BucketNotSelectedError,
    B2BucketOperationError,
    B2FileOperationError,
)
from app.schemas import (
    ApplicationData,
    FileDownloadLink,
    UploadedFileInfo,
)


class B2BucketTypeEnum(StrEnum):
    ALL_PUBLIC = "allPublic"
    ALL_PRIVATE = "allPrivate"
    SNAPSHOT = "snapshot"
    SHARE = "share"
    RESTRICTED = "restricted"


@dataclass(init=False)
class BackBlaze:
    """
    A client for interacting with BackBlaze B2 cloud storage service.

    Provides methods for bucket management and file operations including:
    - Bucket selection, creation, deletion, and updates
    - File upload, download, and deletion
    - URL generation for file access
    """

    b2_raw: B2RawHTTPApi = field(default_factory=lambda: B2RawHTTPApi(B2Http()))
    _bucket: Bucket | None = field(default=None, init=False)
    _b2_api: B2Api = field(default_factory=lambda: B2Api(), init=False)

    def __init__(self, app_data: ApplicationData) -> None:
        """
        Initialize BackBlaze client with application credentials.

        Args:
            app_data: Application data containing app_id and app_key

        Raises:
            B2AuthorizationError: If authorization fails
        """
        self._authorize(app_data)

    @property
    def bucket(self) -> Bucket | None:
        """Get the currently selected bucket."""
        return self._bucket

    def select_bucket(self, bucket_name: str) -> Self:
        """
        Select an existing bucket.

        Args:
            bucket_name: Name of the bucket to select

        Returns:
            Self for method chaining

        Raises:
            B2BucketOperationError: If bucket selection fails
            B2BucketNotFoundError: If the bucket does not exist
            ValueError: If bucket name is empty
        """
        if not bucket_name.strip():
            raise ValueError("Bucket name cannot be empty")

        try:
            self._bucket = self._b2_api.get_bucket_by_name(bucket_name)
            logger.info(f"Successfully selected bucket: {bucket_name}")
            return self
        except NonExistentBucket as ex:
            error_msg = f"Bucket '{bucket_name}' does not exist"
            logger.error(error_msg)
            logger.debug(str(ex))
            raise B2BucketNotFoundError(error_msg, ex) from ex
        except Exception as ex:
            error_msg = f"Failed to select bucket '{bucket_name}'"
            logger.error(error_msg)
            logger.debug(str(ex))
            raise B2BucketNotSelectedError(error_msg, ex) from ex

    def list_buckets(self) -> list[Bucket]:
        """
        List all buckets in the account.

        Returns:
            List of Bucket objects

        Raises:
            B2FileOperationError: If bucket listing fails
        """
        try:
            buckets = self._b2_api.list_buckets()
            logger.info("Successfully retrieved list of buckets")
            return list(buckets)
        except Exception as ex:
            error_msg = "Failed to list buckets"
            logger.error(error_msg)
            logger.debug(str(ex))
            raise B2FileOperationError(error_msg, ex) from ex

    def create_bucket(self, bucket_name: str, bucket_type: B2BucketTypeEnum | None = None) -> Self:
        """
        Create a new bucket.

        Args:
            bucket_name: Unique name for the bucket
            bucket_type: Type of bucket to create

        Returns:
            Self for method chaining

        Raises:
            B2BucketOperationError: If bucket creation fails
            ValueError: If bucket name is empty
        """
        if not bucket_name.strip():
            raise ValueError("Bucket name cannot be empty")

        if bucket_type is None:
            bucket_type = B2BucketTypeEnum.ALL_PRIVATE

        try:
            self._b2_api.create_bucket(name=bucket_name, bucket_type=bucket_type.value)
            logger.info(f"Successfully created bucket: {bucket_name}")
            return self
        except Exception as ex:
            error_msg = f"Failed to create bucket '{bucket_name}'"
            logger.error(error_msg)
            logger.debug(str(ex))
            raise B2FileOperationError(error_msg, ex) from ex

    def delete_selected_bucket(self) -> Self:
        """
        Delete the currently selected bucket.

        Returns:
            Self for method chaining

        Raises:
            B2BucketNotSelectedError: If no bucket is selected
            B2BucketOperationError: If deletion fails
            B2BucketNotFoundError: If the bucket does not exist
        """
        if not self._bucket:
            raise B2BucketNotSelectedError("No bucket is selected for this operation")

        bucket_name = self._bucket.name
        if not bucket_name:
            raise B2BucketNotSelectedError("Selected bucket has no name")

        try:
            bucket = self._b2_api.get_bucket_by_name(bucket_name)
            self._b2_api.delete_bucket(bucket)
            self._bucket = None  # Clear selected bucket
            logger.info(f"Successfully deleted bucket: {bucket_name}")
            return self
        except NonExistentBucket as ex:
            error_msg = f"Bucket '{bucket_name}' does not exist"
            logger.error(error_msg)
            logger.debug(str(ex))
            raise B2BucketNotFoundError(error_msg, ex) from ex
        except Exception as ex:
            error_msg = f"Failed to delete bucket '{bucket_name}'"
            logger.error(error_msg)
            logger.debug(str(ex))
            raise B2BucketOperationError(error_msg, ex) from ex

    def update_selected_bucket(
        self,
        bucket_type: B2BucketTypeEnum | None = None,
        bucket_info: dict | None = None,
    ) -> Self:
        """
        Update properties of the currently selected bucket.

        Args:
            bucket_type: New bucket type
            bucket_info: New bucket info

        Returns:
            Self for method chaining

        Raises:
            B2BucketNotSelectedError: If no bucket is selected
            B2BucketOperationError: If update fails
        """
        if not self._bucket:
            raise B2BucketNotSelectedError("No bucket is selected for this operation")

        if not self._bucket.name:
            raise B2BucketNotSelectedError("Selected bucket has no name")

        try:
            bucket = self._b2_api.get_bucket_by_name(self._bucket.name)
            bucket_type_value = bucket_type.value if bucket_type else None
            bucket.update(bucket_type=bucket_type_value, bucket_info=bucket_info)
            logger.info(f"Successfully updated bucket: {self._bucket.name}")
            return self
        except Exception as ex:
            error_msg = f"Failed to update bucket '{self._bucket.name}'"
            logger.error(error_msg)
            logger.debug(str(ex))
            raise B2BucketOperationError(error_msg, ex) from ex

    def upload_file(
        self,
        local_file_path: str,
        b2_file_name: str,
        file_info: UploadedFileInfo | None = None,
    ) -> FileVersion:
        """
        Upload a file to the selected bucket.

        Args:
            local_file_path: Path to local file
            b2_file_name: Name for the file in B2
            file_info: Optional file metadata

        Returns:
            FileVersion object of uploaded file

        Raises:
            B2BucketNotSelectedError: If no bucket is selected
            B2FileOperationError: If upload fails
            ValueError: If local file path or B2 file name is empty
            FileNotFoundError: If local file does not exist
        """

        if not self._bucket:
            raise B2BucketNotSelectedError("No bucket is selected for this operation")

        self._validate_file_path(local_file_path)

        if not b2_file_name.strip():
            raise ValueError("B2 file name cannot be empty")

        file_info = file_info or UploadedFileInfo(scanned=False)

        bucket_name = self._bucket.name
        if not bucket_name:
            raise B2BucketNotSelectedError("Selected bucket has no name")

        try:
            bucket = self._b2_api.get_bucket_by_name(bucket_name)
            result = bucket.upload_local_file(
                local_file=local_file_path,
                file_name=b2_file_name,
                file_info=file_info.model_dump(),
            )
            logger.info(f"Successfully uploaded file: {b2_file_name}")
            return result
        except Exception as ex:
            self._cleanup_failed_upload(local_file_path)
            error_msg = f"Failed to upload file '{local_file_path}'"
            logger.error(error_msg)
            logger.debug(str(ex))
            raise B2FileOperationError(error_msg, ex) from ex

    def get_download_url_by_name(self, file_name: str) -> FileDownloadLink:
        """
        Get download URL for a file by name.

        Args:
            file_name: Name of the file

        Returns:
            FileDownloadLink object

        Raises:
            B2BucketNotSelectedError: If no bucket is selected
            B2FileOperationError: If URL generation fails
            ValueError: If file name is empty
        """
        if not self._bucket:
            raise B2BucketNotSelectedError("No bucket is selected for this operation")

        if not file_name.strip():
            raise ValueError("File name cannot be empty")

        bucket_name = self._bucket.name
        if not bucket_name:
            raise B2BucketNotSelectedError("Selected bucket has no name")

        try:
            bucket = self._b2_api.get_bucket_by_name(bucket_name)
            download_url = bucket.get_download_url(file_name)
            return FileDownloadLink(download_url=download_url)
        except Exception as ex:
            error_msg = f"Failed to get download URL for file '{file_name}'"
            logger.error(error_msg)
            logger.debug(str(ex))
            raise B2FileOperationError(error_msg, ex) from ex

    def get_download_url_by_file_id(self, file_id: str) -> FileDownloadLink:
        """
        Get download URL for a file by ID.

        Args:
            file_id: ID of the file

        Returns:
            FileDownloadLink object

        Raises:
            B2BucketNotSelectedError: If no bucket is selected
            B2FileOperationError: If URL generation fails
            ValueError: If file ID is empty
        """
        if not file_id.strip():
            raise ValueError("File ID cannot be empty")

        try:
            download_url = self._b2_api.get_download_url_for_fileid(file_id)
            return FileDownloadLink(download_url=download_url)
        except Exception as ex:
            error_msg = f"Failed to get download URL for file ID '{file_id}'"
            logger.error(error_msg)
            logger.debug(str(ex))
            raise B2FileOperationError(error_msg, ex) from ex

    def delete_file(self, file_id: str, file_name: str) -> FileIdAndName:
        """
        Delete a file from the selected bucket.

        Args:
            file_id: ID of the file to delete
            file_name: Name of the file to delete

        Returns:
            FileIdAndName object of deleted file

        Raises:
            B2BucketNotSelectedError: If no bucket is selected
            B2FileOperationError: If deletion fails
            ValueError: If file ID or name is empty
        """
        if not self._bucket:
            raise B2BucketNotSelectedError("No bucket is selected for this operation")

        if not file_id.strip() or not file_name.strip():
            raise ValueError("File ID and name cannot be empty")

        try:
            result = self._b2_api.delete_file_version(file_id=file_id, file_name=file_name)
            logger.info(f"Successfully deleted file: {file_name}")
            return result
        except Exception as ex:
            error_msg = f"Failed to delete file '{file_name}' (ID: {file_id})"
            logger.error(error_msg)
            logger.debug(str(ex))
            raise B2FileOperationError(error_msg, ex) from ex

    def get_temporary_download_link(
        self,
        url: AnyUrl,
        valid_duration_in_seconds: int = 900,
    ) -> FileDownloadLink:
        """
        Get temporary download link with authorization token.

        Args:
            url: Download URL containing file ID
            valid_duration_in_seconds: Link validity duration (default: 15 minutes)

        Returns:
            FileDownloadLink with auth token

        Raises:
            B2BucketNotSelectedError: If no bucket is selected
            B2FileOperationError: If link generation fails
            ValueError: If duration is not positive
            ValueError: If URL does not contain file ID parameter
        """
        if not self._bucket:
            raise B2BucketNotSelectedError("No bucket is selected for this operation")

        if valid_duration_in_seconds <= 0:
            raise ValueError("Duration must be positive")

        file_id = self._extract_file_id_from_url(url)

        try:
            file_info = self._bucket.get_file_info_by_id(file_id)
            auth_token = self._bucket.get_download_authorization(
                file_name_prefix=file_info.file_name,
                valid_duration_in_seconds=valid_duration_in_seconds,
            )
            download_url = self._bucket.get_download_url(file_info.file_name)

            return FileDownloadLink(download_url=download_url, auth_token=auth_token)
        except Exception as ex:
            error_msg = f"Failed to get temporary download link for file ID '{file_id}'"
            logger.error(error_msg)
            logger.debug(str(ex))
            raise B2FileOperationError(error_msg, ex) from ex

    def get_file_details(self, file_id: str) -> FileVersion:
        """
        Get file details by ID.

        Args:
            file_id: ID of the file

        Returns:
            FileVersion object with file details

        Raises:
            B2FileOperationError: If retrieval fails
            ValueError: If file ID is empty
        """
        if not file_id.strip():
            raise ValueError("File ID cannot be empty")

        try:
            return self._b2_api.get_file_info(file_id)
        except Exception as ex:
            error_msg = f"Failed to get file details for ID '{file_id}'"
            logger.error(error_msg)
            logger.debug(str(ex))
            raise B2FileOperationError(error_msg, ex) from ex

    def _authorize(self, app_data: ApplicationData) -> None:
        """
        Authorize with BackBlaze B2 service.
        Args:
            app_data: Application data containing app_id and app_key
        Raises:
            B2AuthorizationError: If authorization fails
        """
        try:
            self._b2_api.authorize_account(
                realm="production",
                application_key_id=app_data.app_id,
                application_key=app_data.app_key,
            )
            logger.info("Successfully authorized BackBlaze account")
        except Exception as ex:
            logger.error("Failed to authorize BackBlaze account")
            logger.debug(str(ex))
            raise B2AuthorizationError("Failed to authorize BackBlaze account", ex) from ex

    @staticmethod
    def _validate_file_path(file_path: str) -> None:
        """
        Validate the local file path.
        Args:
            file_path: Path to the local file
        Raises:
            ValueError: If file path is empty
            FileNotFoundError: If file does not exist
        """
        if not file_path.strip():
            raise ValueError("File path cannot be empty")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

    @staticmethod
    def _cleanup_failed_upload(local_file_path: str) -> None:
        """
        Clean up local file after failed upload.
        Args:
            local_file_path: Path to the local file
        """
        try:
            if os.path.exists(local_file_path):
                os.remove(local_file_path)
                logger.info(f"Cleaned up local file after failed upload: {local_file_path}")
        except OSError as ex:
            logger.warning(f"Failed to clean up local file: {local_file_path}")
            logger.debug(str(ex))

    @staticmethod
    def _extract_file_id_from_url(url: AnyUrl) -> str:
        """
        Extract file ID from URL.
        Args:
            url: Download URL containing file ID
        Returns:
            Extracted file ID as string
        Raises:
            ValueError: If URL does not contain file ID parameter
        """
        url_str = str(url)
        if "fileId=" not in url_str:
            raise ValueError("URL does not contain file ID parameter")
        return url_str.split("fileId=")[-1]
