import asyncio
import json
import mimetypes
import os
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import AsyncGenerator

import aiofiles
from gcloud.aio.storage import Bucket, Storage
from loguru import logger
from pydantic import HttpUrl, ValidationError

from app.core.exceptions.gcs_exceptions import (
    GCSError,
)
from app.schemas import (
    BucketFile,
    BucketFolder,
    ServiceAccount,
)


@dataclass(init=False)
class GCS:
    """
    Async GCS client for Google Cloud Storage operations.

    Example usage:
        async with GCS(service_account_info) as gcs_client:
            await gcs_client.upload_file(...)
            await gcs_client.download_file(...)
    """

    __storage: Storage | None = field(default=None)
    __service_account_info: dict | str | None = field(default=None)

    def __init__(
        self,
        service_account_info: ServiceAccount | Path | str,
    ):
        """
        Async GCS client for Google Cloud Storage operations.

        Example usage:
            async with GCS(service_account_info) as gcs_client:
                await gcs_client.upload_file(...)
                await gcs_client.download_file(...)

        Args:
            service_account_info (ServiceAccount | Path | str): Service account details or path to JSON file.

        Raises:
            NotImplementedError: If the provided service_account_info type is not supported.
        """
        if isinstance(service_account_info, (str, Path)):
            self.__service_account_info = str(service_account_info)
        elif isinstance(service_account_info, ServiceAccount):
            self.__service_account_info = {
                "type": "service_account",
                "project_id": service_account_info.project_id,
                "private_key_id": service_account_info.private_key_id,
                "private_key": service_account_info.private_key,
                "client_email": service_account_info.client_email,
                "client_id": service_account_info.client_id,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            }
        else:
            raise NotImplementedError("Parameter not supported")

    async def __aenter__(self):
        """Async context manager entry"""
        self.__storage = Storage(service_file=json.dumps(self.__service_account_info))

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.__storage:
            await self.__storage.close()

    @property
    def storage(self) -> Storage:
        if self.__storage is None:
            raise GCSError("GCS storage client is not initialized. Use async context manager.")

        return self.__storage

    async def get_all_buckets(self, project: str) -> list[Bucket]:
        """
        Get all buckets in the project

        Args:
            project (str): GCP project ID

        Returns:
            List of Bucket objects
        """

        return await self.storage.list_buckets(project=project)

    async def upload_file(
        self,
        bucket_name: str,
        file_path: str,
        bucket_folder_path: str,
        content_type: str | None = None,
    ) -> BucketFile | None:
        """
        Upload a file to GCS bucket

        Args:
            bucket_name (str): Name of the GCS bucket
            file_path (str): Local file path
            bucket_folder_path (str): Destination folder path in bucket
            content_type (str | None): MIME type of the file

        Returns:
            BucketFile or None
        """

        if not os.path.exists(file_path):
            raise ValueError(f"File {file_path} not found")

        if not bucket_folder_path.endswith("/"):
            bucket_folder_path += "/"

        filename = os.path.basename(file_path)
        object_name = bucket_folder_path + filename

        if content_type is None:
            content_type, _ = mimetypes.guess_type(filename)

        async with aiofiles.open(file_path, "rb") as f:
            file_data = await f.read()

        await self.storage.upload(
            bucket=bucket_name,
            object_name=object_name,
            file_data=file_data,
            content_type=content_type,
        )

        logger.info(f"Uploaded {filename} to {object_name}")
        return await self.get_file(bucket_name, object_name)

    async def upload_bytesio(
        self,
        bucket_name: str,
        bytes_io: BytesIO,
        target_filename: str,
        bucket_folder_path: str,
        content_type: str | None = None,
    ) -> BucketFile | None:
        """
        Upload BytesIO object to GCS

        Args:
            bucket_name (str): Name of the GCS bucket
            bytes_io (BytesIO): BytesIO object containing file data
            target_filename (str): Target filename in bucket
            bucket_folder_path (str): Destination folder path
            content_type (str | None): MIME type

        Returns:
            BucketFile or None
        """

        if not bucket_folder_path.endswith("/"):
            bucket_folder_path += "/"

        object_name = f"{bucket_folder_path}{target_filename}"

        bytes_io.seek(0)
        file_data = bytes_io.read()
        bytes_io.seek(0)

        await self.storage.upload(
            bucket=bucket_name,
            object_name=object_name,
            file_data=file_data,
            content_type=content_type,
        )

        logger.info(f"Uploaded {target_filename} to {object_name}")
        return await self.get_file(bucket_name, object_name)

    async def download_file(
        self,
        bucket_name: str,
        file_path_in_bucket: str,
        destination_path: str,
    ) -> None:
        """
        Download file from GCS to local path

        Args:
            bucket_name (str): Name of the GCS bucket
            file_path_in_bucket (str): Path of file in bucket
            destination_path (str): Local destination path
        """

        file_data = await self.storage.download(
            bucket=bucket_name,
            object_name=file_path_in_bucket,
        )

        os.makedirs(os.path.dirname(destination_path), exist_ok=True)

        async with aiofiles.open(destination_path, "wb") as f:
            await f.write(file_data)

        logger.info(f"Downloaded {file_path_in_bucket} to {destination_path}")

    async def download_file_bytes(
        self, bucket_name: str, file_path_in_bucket: str
    ) -> BytesIO | None:
        """
        Download file as BytesIO object

        Args:
            bucket_name (str): Name of the GCS bucket
            file_path_in_bucket (str): Path of file in bucket

        Returns:
            BytesIO object or None
        """

        try:
            file_data = await self.storage.download(
                bucket=bucket_name,
                object_name=file_path_in_bucket,
            )
            return BytesIO(file_data)
        except Exception as e:
            logger.exception(f"Failed to download {file_path_in_bucket}: {e}")
            return None

    async def create_folder(
        self,
        bucket_name: str,
        folder_path_in_bucket: str,
    ) -> None:
        """
        Create a folder in GCS bucket

        Args:
            bucket_name (str): Name of the GCS bucket
            folder_path_in_bucket (str): Folder path to create
        """

        if not folder_path_in_bucket.endswith("/"):
            folder_path_in_bucket += "/"

        await self.storage.upload(
            bucket=bucket_name,
            object_name=folder_path_in_bucket,
            file_data=b"",
            content_type="application/x-www-form-urlencoded;charset=UTF-8",
        )

        logger.info(f"Created folder {folder_path_in_bucket}")

    async def list_folders(
        self,
        bucket_name: str,
        parent_folder_path_in_bucket: str = "",
    ) -> AsyncGenerator[BucketFolder, None]:
        """
        List folders in bucket

        Args:
            bucket_name (str): Name of the GCS bucket
            parent_folder_path_in_bucket (str): Parent folder path in bucket

        Yields:
            BucketFolder objects
        """
        if parent_folder_path_in_bucket and not parent_folder_path_in_bucket.endswith("/"):
            parent_folder_path_in_bucket += "/"
        blob_names = await self.storage.list_objects(
            bucket=bucket_name + parent_folder_path_in_bucket,
        )

        for blob_name in blob_names.get("items", {}):
            name: str = blob_name.get("name", "")
            if name and name.endswith("/"):
                yield BucketFolder(
                    name=os.path.basename(name[:-1]),
                    bucket_folder_path=name,
                )

    async def get_file(self, bucket_name: str, file_path_in_bucket: str) -> BucketFile | None:
        """
        Get file metadata

        Args:
            bucket_name (str): Name of the GCS bucket
            file_path_in_bucket (str): Path of file in bucket

        Returns:
            BucketFile object or None
        """

        try:
            metadata = await self.storage.download_metadata(
                bucket=bucket_name,
                object_name=file_path_in_bucket,
            )
        except Exception as e:
            logger.exception(f"Failed to download metadata for {file_path_in_bucket}")
            return None

        try:
            public_url = HttpUrl(
                f"https://storage.googleapis.com/{bucket_name}/{file_path_in_bucket}"
            )
            authenticated_url = HttpUrl(
                f"https://storage.cloud.google.com/{bucket_name}/{file_path_in_bucket}"
            )
        except ValidationError as e:
            logger.exception(f"Invalid URL for {file_path_in_bucket}")
            return None

        return BucketFile(
            id=metadata.get("id", 0),
            basename=os.path.basename(file_path_in_bucket),
            extension=os.path.splitext(file_path_in_bucket)[1],
            file_path_in_bucket=file_path_in_bucket,
            bucket_name=bucket_name,
            public_url=public_url,
            authenticated_url=authenticated_url,
            size_bytes=int(metadata.get("size", 0)),
            creation_date=metadata.get("timeCreated", datetime.min),
            modification_date=metadata.get("updated", datetime.min),
            md5_hash=metadata.get("md5Hash"),
            crc32c_checksum=metadata.get("crc32c"),
            content_type=metadata.get("contentType"),
            metadata=metadata.get("metadata", {}),
        )

    async def list_files(
        self,
        bucket_name: str,
        folder_path_in_bucket: str = "",
    ) -> AsyncGenerator[BucketFile, None]:
        """
        List files in bucket folder

        Args:
            bucket_name (str): Name of the GCS bucket
            folder_path_in_bucket (str): Folder path (prefix) in bucket

        Yields:
            BucketFile objects
        """

        if folder_path_in_bucket and not folder_path_in_bucket.endswith("/"):
            folder_path_in_bucket += "/"

        blob_names = await self.storage.list_objects(
            bucket=bucket_name,
        )

        for blob_name in blob_names.get("items", {}):
            name: str = blob_name.get("name", "")

            if name and not name.endswith("/"):
                file_info = await self.get_file(bucket_name, name)
                if file_info:
                    yield file_info

    async def delete_file(self, bucket_name: str, file_path_in_bucket: str) -> None:
        """
        Delete a file from bucket

        Args:
            bucket_name (str): Name of the GCS bucket
            file_path_in_bucket (str): Path of file in bucket
        """

        await self.storage.delete(
            bucket=bucket_name,
            object_name=file_path_in_bucket,
        )

        logger.info(f"Deleted {file_path_in_bucket}")

    async def delete_files(self, bucket_name: str, file_paths: list[str]) -> None:
        """
        Delete multiple files

        Args:
            bucket_name (str): Name of the GCS bucket
            file_paths (list[str]): List of file paths to delete
        """

        tasks = [self.delete_file(bucket_name, file_path) for file_path in file_paths]
        await asyncio.gather(*tasks)

    async def copy_file(
        self,
        bucket_name: str,
        source_path: str,
        destination_path: str,
        destination_bucket: str | None = None,
    ) -> None:
        """
        Copy file within bucket or to another bucket

        Args:
            bucket_name (str): Name of the GCS bucket
            source_path (str): Source file path
            destination_path (str): Destination file path
            destination_bucket (str | None): Destination bucket (None = same bucket)
        """
        dest_bucket = destination_bucket or bucket_name

        await self.storage.copy(
            bucket=bucket_name,
            object_name=source_path,
            destination_bucket=dest_bucket,
            new_name=destination_path,
        )

        logger.info(f"Copied {source_path} to {destination_path}")

    async def move_file(
        self,
        bucket_name: str,
        source_path: str,
        destination_path: str,
        destination_bucket: str | None = None,
    ) -> None:
        """
        Move file (copy + delete)

        Args:
            bucket_name (str): Name of the GCS bucket
            source_path (str): Source file path
            destination_path (str): Destination file path
            destination_bucket (str | None): Destination bucket (None = same bucket)
        """
        await self.copy_file(bucket_name, source_path, destination_path, destination_bucket)
        await self.delete_file(bucket_name, source_path)
        logger.info(f"Moved {source_path} to {destination_path}")
