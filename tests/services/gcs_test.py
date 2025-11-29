from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from faker import Faker
from pydantic import ValidationError

from app.core.exceptions.gcs_exceptions import GCSError
from app.schemas import ServiceAccount
from app.services.gcs import GCS


class TestGCSInitialization:
    """Test GCS initialization."""

    def test_init_with_service_account_object(self, gcs_service_account: ServiceAccount):
        """Test GCS init with ServiceAccount object."""
        gcs = GCS(gcs_service_account)
        assert gcs._GCS__service_account_info is not None
        assert isinstance(gcs._GCS__service_account_info, dict)

    def test_init_with_path_string(self, tmp_path: Path):
        """Test GCS init with path string."""
        service_account_file = tmp_path / "service_account.json"
        service_account_file.write_text('{"type": "service_account"}')

        gcs = GCS(str(service_account_file))
        assert gcs._GCS__service_account_info == str(service_account_file)

    def test_init_with_path_object(self, tmp_path: Path):
        """Test GCS init with Path object."""
        service_account_file = tmp_path / "service_account.json"
        service_account_file.write_text('{"type": "service_account"}')

        gcs = GCS(service_account_file)
        assert gcs._GCS__service_account_info == str(service_account_file)

    def test_init_with_invalid_type(self):
        """Test GCS init with unsupported type."""
        with pytest.raises(NotImplementedError) as exc_info:
            GCS(123)  # type: ignore

        assert "Parameter not supported" in str(exc_info.value)


class TestGCSContextManager:
    """Test GCS async context manager."""

    @pytest.mark.anyio
    async def test_context_manager_enter_exit(
        self, gcs_service_account: ServiceAccount, mock_gcs_storage: AsyncMock
    ):
        """Test GCS context manager enter and exit."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            async with GCS(gcs_service_account) as gcs:
                assert gcs._GCS__storage is not None

            mock_gcs_storage.close.assert_called_once()

    @pytest.mark.anyio
    async def test_storage_property_when_initialized(
        self, gcs_service_account: ServiceAccount, mock_gcs_storage: AsyncMock
    ):
        """Test storage property when initialized."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            async with GCS(gcs_service_account) as gcs:
                storage = gcs.storage
                assert storage == mock_gcs_storage

    @pytest.mark.anyio
    async def test_storage_property_when_not_initialized(self, gcs_service_account: ServiceAccount):
        """Test storage property raises error when not initialized."""
        gcs = GCS(gcs_service_account)

        with pytest.raises(GCSError) as exc_info:
            _ = gcs.storage

        assert "not initialized" in str(exc_info.value)


class TestGCSBucketOperations:
    """Test GCS bucket operations."""

    @pytest.mark.anyio
    async def test_get_all_buckets(
        self,
        gcs_service_account: ServiceAccount,
        mock_gcs_storage: AsyncMock,
        mock_gcs_bucket: Mock,
    ):
        """Test get_all_buckets."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            mock_gcs_storage.list_buckets = AsyncMock(return_value=[mock_gcs_bucket])

            async with GCS(gcs_service_account) as gcs:
                result = await gcs.get_all_buckets("test-project")

                assert len(result) == 1
                assert result[0] == mock_gcs_bucket


class TestGCSFileOperations:
    """Test GCS file operations."""

    @pytest.mark.anyio
    async def test_upload_file_success(
        self,
        gcs_service_account: ServiceAccount,
        mock_gcs_storage: AsyncMock,
        temp_test_file: Path,
        sample_bucket_file,
    ):
        """Test successful file upload."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            mock_gcs_storage.upload = AsyncMock()

            async with GCS(gcs_service_account) as gcs:
                with patch.object(gcs, "get_file", new_callable=AsyncMock) as mock_get_file:
                    mock_get_file.return_value = sample_bucket_file

                    result = await gcs.upload_file("test-bucket", str(temp_test_file), "folder/")

                    assert result == sample_bucket_file
                    mock_gcs_storage.upload.assert_called_once()

    @pytest.mark.anyio
    async def test_upload_file_not_found(
        self, gcs_service_account: ServiceAccount, mock_gcs_storage: AsyncMock
    ):
        """Test upload_file with nonexistent file."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            async with GCS(gcs_service_account) as gcs:
                with pytest.raises(ValueError) as exc_info:
                    await gcs.upload_file("test-bucket", "/nonexistent/file.txt", "folder/")

                assert "not found" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_upload_file_with_content_type(
        self,
        gcs_service_account: ServiceAccount,
        mock_gcs_storage: AsyncMock,
        temp_test_file: Path,
        sample_bucket_file,
    ):
        """Test file upload with custom content type."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            mock_gcs_storage.upload = AsyncMock()

            async with GCS(gcs_service_account) as gcs:
                with patch.object(gcs, "get_file", new_callable=AsyncMock) as mock_get_file:
                    mock_get_file.return_value = sample_bucket_file

                    result = await gcs.upload_file(
                        "test-bucket",
                        str(temp_test_file),
                        "folder/",
                        content_type="application/json",
                    )

                    assert result == sample_bucket_file

    @pytest.mark.anyio
    async def test_upload_bytesio_success(
        self,
        gcs_service_account: ServiceAccount,
        mock_gcs_storage: AsyncMock,
        sample_file_bytes: BytesIO,
        sample_bucket_file,
    ):
        """Test successful BytesIO upload."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            mock_gcs_storage.upload = AsyncMock()

            async with GCS(gcs_service_account) as gcs:
                with patch.object(gcs, "get_file", new_callable=AsyncMock) as mock_get_file:
                    mock_get_file.return_value = sample_bucket_file

                    result = await gcs.upload_bytesio(
                        "test-bucket", sample_file_bytes, "test.txt", "folder/"
                    )

                    assert result == sample_bucket_file

    @pytest.mark.anyio
    async def test_download_file_success(
        self, gcs_service_account: ServiceAccount, mock_gcs_storage: AsyncMock, tmp_path: Path
    ):
        """Test successful file download."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            mock_gcs_storage.download = AsyncMock(return_value=b"test content")

            destination = tmp_path / "downloaded_file.txt"

            async with GCS(gcs_service_account) as gcs:
                await gcs.download_file("test-bucket", "file.txt", str(destination))

                assert destination.exists()
                assert destination.read_text() == "test content"

    @pytest.mark.anyio
    async def test_download_file_bytes_success(
        self, gcs_service_account: ServiceAccount, mock_gcs_storage: AsyncMock
    ):
        """Test successful file download as bytes."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            mock_gcs_storage.download = AsyncMock(return_value=b"test content")

            async with GCS(gcs_service_account) as gcs:
                result = await gcs.download_file_bytes("test-bucket", "file.txt")

                assert result is not None
                assert result.read() == b"test content"

    @pytest.mark.anyio
    async def test_download_file_bytes_failure(
        self, gcs_service_account: ServiceAccount, mock_gcs_storage: AsyncMock
    ):
        """Test file download as bytes with exception."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            mock_gcs_storage.download = AsyncMock(side_effect=Exception("Download failed"))

            async with GCS(gcs_service_account) as gcs:
                result = await gcs.download_file_bytes("test-bucket", "file.txt")

                assert result is None

    @pytest.mark.anyio
    async def test_create_folder(
        self, gcs_service_account: ServiceAccount, mock_gcs_storage: AsyncMock
    ):
        """Test folder creation."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            mock_gcs_storage.upload = AsyncMock()

            async with GCS(gcs_service_account) as gcs:
                await gcs.create_folder("test-bucket", "new_folder")

                mock_gcs_storage.upload.assert_called_once()

    @pytest.mark.anyio
    async def test_get_file_success(
        self,
        gcs_service_account: ServiceAccount,
        mock_gcs_storage: AsyncMock,
        faker_instance: Faker,
    ):
        """Test successful get_file."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            metadata = {
                "id": faker_instance.uuid4(),
                "name": "test.txt",
                "size": "1024",
                "timeCreated": "2023-01-01T00:00:00Z",
                "updated": "2023-01-01T00:00:00Z",
                "md5Hash": faker_instance.md5(),
                "crc32c": "AAAAAA==",  # Valid base64-encoded CRC32C
                "contentType": "text/plain",
                "metadata": {},
            }
            mock_gcs_storage.download_metadata = AsyncMock(return_value=metadata)

            async with GCS(gcs_service_account) as gcs:
                result = await gcs.get_file("test-bucket", "test.txt")

                assert result is not None
                assert result.basename == "test.txt"

    @pytest.mark.anyio
    async def test_get_file_download_metadata_failure(
        self, gcs_service_account: ServiceAccount, mock_gcs_storage: AsyncMock
    ):
        """Test get_file with metadata download failure."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            mock_gcs_storage.download_metadata = AsyncMock(side_effect=Exception("Failed"))

            async with GCS(gcs_service_account) as gcs:
                result = await gcs.get_file("test-bucket", "test.txt")

                assert result is None

    @pytest.mark.anyio
    async def test_get_file_validation_error(
        self, gcs_service_account: ServiceAccount, mock_gcs_storage: AsyncMock
    ):
        """Test get_file with URL validation error."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            metadata = {"id": "123", "name": "test.txt", "size": "1024"}
            mock_gcs_storage.download_metadata = AsyncMock(return_value=metadata)

            async with GCS(gcs_service_account) as gcs:
                with patch(
                    "app.services.gcs.HttpUrl",
                    side_effect=ValidationError.from_exception_data("test", []),
                ):
                    result = await gcs.get_file("test-bucket", "test.txt")

                    assert result is None

    @pytest.mark.anyio
    async def test_list_files(
        self, gcs_service_account: ServiceAccount, mock_gcs_storage: AsyncMock, sample_bucket_file
    ):
        """Test list_files."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            mock_gcs_storage.list_objects = AsyncMock(
                return_value={"items": [{"name": "file1.txt"}, {"name": "file2.txt"}]}
            )

            async with GCS(gcs_service_account) as gcs:
                with patch.object(gcs, "get_file", new_callable=AsyncMock) as mock_get_file:
                    mock_get_file.return_value = sample_bucket_file

                    files = []
                    async for file in gcs.list_files("test-bucket"):
                        files.append(file)

                    assert len(files) == 2

    @pytest.mark.anyio
    async def test_list_folders(
        self, gcs_service_account: ServiceAccount, mock_gcs_storage: AsyncMock
    ):
        """Test list_folders."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            mock_gcs_storage.list_objects = AsyncMock(
                return_value={"items": [{"name": "folder1/"}, {"name": "folder2/"}]}
            )

            async with GCS(gcs_service_account) as gcs:
                folders = []
                async for folder in gcs.list_folders("test-bucket"):
                    folders.append(folder)

                assert len(folders) == 2

    @pytest.mark.anyio
    async def test_delete_file(
        self, gcs_service_account: ServiceAccount, mock_gcs_storage: AsyncMock
    ):
        """Test delete_file."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            mock_gcs_storage.delete = AsyncMock()

            async with GCS(gcs_service_account) as gcs:
                await gcs.delete_file("test-bucket", "file.txt")

                mock_gcs_storage.delete.assert_called_once()

    @pytest.mark.anyio
    async def test_delete_files(
        self, gcs_service_account: ServiceAccount, mock_gcs_storage: AsyncMock
    ):
        """Test delete_files."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            mock_gcs_storage.delete = AsyncMock()

            async with GCS(gcs_service_account) as gcs:
                await gcs.delete_files("test-bucket", ["file1.txt", "file2.txt"])

                assert mock_gcs_storage.delete.call_count == 2

    @pytest.mark.anyio
    async def test_copy_file_same_bucket(
        self, gcs_service_account: ServiceAccount, mock_gcs_storage: AsyncMock
    ):
        """Test copy_file within same bucket."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            mock_gcs_storage.copy = AsyncMock()

            async with GCS(gcs_service_account) as gcs:
                await gcs.copy_file("test-bucket", "source.txt", "destination.txt")

                mock_gcs_storage.copy.assert_called_once()

    @pytest.mark.anyio
    async def test_copy_file_different_bucket(
        self, gcs_service_account: ServiceAccount, mock_gcs_storage: AsyncMock
    ):
        """Test copy_file to different bucket."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            mock_gcs_storage.copy = AsyncMock()

            async with GCS(gcs_service_account) as gcs:
                await gcs.copy_file(
                    "test-bucket",
                    "source.txt",
                    "destination.txt",
                    destination_bucket="other-bucket",
                )

                mock_gcs_storage.copy.assert_called_once()

    @pytest.mark.anyio
    async def test_move_file(
        self, gcs_service_account: ServiceAccount, mock_gcs_storage: AsyncMock
    ):
        """Test move_file."""
        with patch("app.services.gcs.Storage", return_value=mock_gcs_storage):
            mock_gcs_storage.copy = AsyncMock()
            mock_gcs_storage.delete = AsyncMock()

            async with GCS(gcs_service_account) as gcs:
                await gcs.move_file("test-bucket", "source.txt", "destination.txt")

                mock_gcs_storage.copy.assert_called_once()
                mock_gcs_storage.delete.assert_called_once()
