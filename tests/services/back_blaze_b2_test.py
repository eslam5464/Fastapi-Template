from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from b2sdk.v2 import FileIdAndName
from b2sdk.v2.exception import NonExistentBucket
from faker import Faker
from pydantic import AnyUrl

from app.core.exceptions.back_blaze_exceptions import (
    B2AuthorizationError,
    B2BucketNotFoundError,
    B2BucketNotSelectedError,
    B2BucketOperationError,
    B2FileOperationError,
)
from app.schemas import ApplicationData, UploadedFileInfo
from app.services.back_blaze_b2 import B2BucketTypeEnum, BackBlaze


class TestBackBlazeInitialization:
    """Test BackBlaze initialization."""

    def test_init_with_app_data(self, b2_app_data: ApplicationData):
        """Test BackBlaze initialization with application data."""
        bb = BackBlaze(b2_app_data)
        assert bb._app_data == b2_app_data
        assert bb._authorized is False
        assert bb._bucket is None

    def test_bucket_property_when_none(self, b2_app_data: ApplicationData):
        """Test bucket property returns None when not selected."""
        bb = BackBlaze(b2_app_data)
        assert bb.bucket is None


class TestBackBlazeAuthorization:
    """Test BackBlaze authorization."""

    @pytest.mark.anyio
    async def test_ensure_authorized_success(self, b2_app_data: ApplicationData, mock_b2_api: Mock):
        """Test successful authorization."""
        bb = BackBlaze(b2_app_data)
        bb._b2_api = mock_b2_api

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = None
            await bb.ensure_authorized()

            assert bb._authorized is True
            mock_to_thread.assert_called_once()

    @pytest.mark.anyio
    async def test_ensure_authorized_already_authorized(self, b2_app_data: ApplicationData):
        """Test ensure_authorized when already authorized."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True

        with patch.object(bb, "_authorize") as mock_authorize:
            await bb.ensure_authorized()
            mock_authorize.assert_not_called()

    @pytest.mark.anyio
    async def test_authorize_failure(self, b2_app_data: ApplicationData, mock_b2_api: Mock):
        """Test authorization failure."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.side_effect = Exception("Auth failed")

                with pytest.raises(B2AuthorizationError) as exc_info:
                    await bb._authorize()

                assert "Failed to authorize BackBlaze account" in str(exc_info.value)
                assert bb._authorized is False


class TestBackBlazeBucketOperations:
    """Test BackBlaze bucket operations."""

    @pytest.mark.anyio
    async def test_select_bucket_success(
        self, b2_app_data: ApplicationData, mock_b2_api: Mock, mock_b2_bucket: Mock
    ):
        """Test successful bucket selection."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._b2_api = mock_b2_api
            bb._authorized = True

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = mock_b2_bucket
                result = await bb.select_bucket("test-bucket")

                assert result is bb
                assert bb._bucket == mock_b2_bucket
                mock_to_thread.assert_called_once()

    @pytest.mark.anyio
    async def test_select_bucket_empty_name(self, b2_app_data: ApplicationData):
        """Test select_bucket with empty bucket name."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True

        with pytest.raises(ValueError) as exc_info:
            await bb.select_bucket("")

        assert "Bucket name cannot be empty" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_select_bucket_whitespace_name(self, b2_app_data: ApplicationData):
        """Test select_bucket with whitespace bucket name."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True

        with pytest.raises(ValueError) as exc_info:
            await bb.select_bucket("   ")

        assert "Bucket name cannot be empty" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_select_bucket_not_found(self, b2_app_data: ApplicationData, mock_b2_api: Mock):
        """Test select_bucket when bucket doesn't exist."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._b2_api = mock_b2_api
            bb._authorized = True

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.side_effect = NonExistentBucket("Bucket not found")

                with pytest.raises(B2BucketNotFoundError) as exc_info:
                    await bb.select_bucket("nonexistent-bucket")

                assert "does not exist" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_select_bucket_other_exception(
        self, b2_app_data: ApplicationData, mock_b2_api: Mock
    ):
        """Test select_bucket with other exception."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._authorized = True

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.side_effect = Exception("Network error")

                with pytest.raises(B2BucketNotSelectedError) as exc_info:
                    await bb.select_bucket("test-bucket")

                assert "Failed to select bucket" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_list_buckets_success(
        self, b2_app_data: ApplicationData, mock_b2_api: Mock, mock_b2_bucket: Mock
    ):
        """Test successful bucket listing."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._b2_api = mock_b2_api
            bb._authorized = True

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = [mock_b2_bucket]
                result = await bb.list_buckets()

                assert len(result) == 1
                assert result[0] == mock_b2_bucket

    @pytest.mark.anyio
    async def test_list_buckets_failure(self, b2_app_data: ApplicationData, mock_b2_api: Mock):
        """Test bucket listing failure."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._authorized = True

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.side_effect = Exception("API error")

                with pytest.raises(B2FileOperationError) as exc_info:
                    await bb.list_buckets()

                assert "Failed to list buckets" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_create_bucket_success(self, b2_app_data: ApplicationData, mock_b2_api: Mock):
        """Test successful bucket creation."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._b2_api = mock_b2_api
            bb._authorized = True

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = None
                result = await bb.create_bucket("new-bucket")

                assert result is bb
                mock_to_thread.assert_called_once()

    @pytest.mark.anyio
    async def test_create_bucket_with_type(self, b2_app_data: ApplicationData, mock_b2_api: Mock):
        """Test bucket creation with specific type."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._b2_api = mock_b2_api
            bb._authorized = True

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = None
                result = await bb.create_bucket("new-bucket", B2BucketTypeEnum.ALL_PUBLIC)

                assert result is bb

    @pytest.mark.anyio
    async def test_create_bucket_empty_name(self, b2_app_data: ApplicationData):
        """Test create_bucket with empty name."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True

        with pytest.raises(ValueError) as exc_info:
            await bb.create_bucket("")

        assert "Bucket name cannot be empty" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_create_bucket_failure(self, b2_app_data: ApplicationData, mock_b2_api: Mock):
        """Test bucket creation failure."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._authorized = True

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.side_effect = Exception("Creation failed")

                with pytest.raises(B2FileOperationError) as exc_info:
                    await bb.create_bucket("new-bucket")

                assert "Failed to create bucket" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_delete_selected_bucket_success(
        self, b2_app_data: ApplicationData, mock_b2_api: Mock, mock_b2_bucket: Mock
    ):
        """Test successful bucket deletion."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._b2_api = mock_b2_api
            bb._authorized = True
            bb._bucket = mock_b2_bucket

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = mock_b2_bucket
                result = await bb.delete_selected_bucket()

                assert result is bb
                assert bb._bucket is None

    @pytest.mark.anyio
    async def test_delete_selected_bucket_no_selection(self, b2_app_data: ApplicationData):
        """Test delete_selected_bucket without bucket selection."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True

        with pytest.raises(B2BucketNotSelectedError) as exc_info:
            await bb.delete_selected_bucket()

        assert "No bucket is selected" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_delete_selected_bucket_no_name(
        self, b2_app_data: ApplicationData, mock_b2_bucket: Mock
    ):
        """Test delete_selected_bucket when bucket has no name."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True
        mock_b2_bucket.name = None
        bb._bucket = mock_b2_bucket

        with pytest.raises(B2BucketNotSelectedError) as exc_info:
            await bb.delete_selected_bucket()

        assert "Selected bucket has no name" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_delete_selected_bucket_not_found(
        self, b2_app_data: ApplicationData, mock_b2_api: Mock, mock_b2_bucket: Mock
    ):
        """Test delete_selected_bucket when bucket doesn't exist."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._b2_api = mock_b2_api
            bb._authorized = True
            bb._bucket = mock_b2_bucket

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.side_effect = NonExistentBucket("Not found")

                with pytest.raises(B2BucketNotFoundError) as exc_info:
                    await bb.delete_selected_bucket()

                assert "does not exist" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_delete_selected_bucket_failure(
        self, b2_app_data: ApplicationData, mock_b2_api: Mock, mock_b2_bucket: Mock
    ):
        """Test delete_selected_bucket failure."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._authorized = True
            bb._bucket = mock_b2_bucket

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.side_effect = Exception("Deletion failed")

                with pytest.raises(B2BucketOperationError) as exc_info:
                    await bb.delete_selected_bucket()

                assert "Failed to delete bucket" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_update_selected_bucket_success(
        self, b2_app_data: ApplicationData, mock_b2_api: Mock, mock_b2_bucket: Mock
    ):
        """Test successful bucket update."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._b2_api = mock_b2_api
            bb._authorized = True
            bb._bucket = mock_b2_bucket

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = mock_b2_bucket
                result = await bb.update_selected_bucket(bucket_type=B2BucketTypeEnum.ALL_PUBLIC)

                assert result is bb

    @pytest.mark.anyio
    async def test_update_selected_bucket_no_selection(self, b2_app_data: ApplicationData):
        """Test update_selected_bucket without bucket selection."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True

        with pytest.raises(B2BucketNotSelectedError) as exc_info:
            await bb.update_selected_bucket()

        assert "No bucket is selected" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_update_selected_bucket_no_name(
        self, b2_app_data: ApplicationData, mock_b2_bucket: Mock
    ):
        """Test update_selected_bucket when bucket has no name."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True
        mock_b2_bucket.name = None
        bb._bucket = mock_b2_bucket

        with pytest.raises(B2BucketNotSelectedError) as exc_info:
            await bb.update_selected_bucket()

        assert "Selected bucket has no name" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_update_selected_bucket_failure(
        self, b2_app_data: ApplicationData, mock_b2_api: Mock, mock_b2_bucket: Mock
    ):
        """Test update_selected_bucket failure."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._authorized = True
            bb._bucket = mock_b2_bucket

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.side_effect = Exception("Update failed")

                with pytest.raises(B2BucketOperationError) as exc_info:
                    await bb.update_selected_bucket()

                assert "Failed to update bucket" in str(exc_info.value)


class TestBackBlazeFileOperations:
    """Test BackBlaze file operations."""

    @pytest.mark.anyio
    async def test_upload_file_success(
        self,
        b2_app_data: ApplicationData,
        mock_b2_api: Mock,
        mock_b2_bucket: Mock,
        temp_test_file: Path,
        mock_b2_file_version: Mock,
    ):
        """Test successful file upload."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._b2_api = mock_b2_api
            bb._authorized = True
            bb._bucket = mock_b2_bucket

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                # First call gets bucket, second call uploads file
                mock_to_thread.side_effect = [mock_b2_bucket, mock_b2_file_version]
                result = await bb.upload_file(str(temp_test_file), "remote_file.txt")

                assert result == mock_b2_file_version

    @pytest.mark.anyio
    async def test_upload_file_no_bucket_selected(
        self, b2_app_data: ApplicationData, temp_test_file: Path
    ):
        """Test upload_file without bucket selection."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True

        with pytest.raises(B2BucketNotSelectedError) as exc_info:
            await bb.upload_file(str(temp_test_file), "remote_file.txt")

        assert "No bucket is selected" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_upload_file_empty_local_path(
        self, b2_app_data: ApplicationData, mock_b2_bucket: Mock
    ):
        """Test upload_file with empty local file path."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True
        bb._bucket = mock_b2_bucket

        with pytest.raises(ValueError) as exc_info:
            await bb.upload_file("", "remote_file.txt")

        assert "File path cannot be empty" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_upload_file_nonexistent_file(
        self, b2_app_data: ApplicationData, mock_b2_bucket: Mock
    ):
        """Test upload_file with nonexistent file."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True
        bb._bucket = mock_b2_bucket

        with pytest.raises(FileNotFoundError) as exc_info:
            await bb.upload_file("/nonexistent/file.txt", "remote_file.txt")

        assert "File not found" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_upload_file_empty_b2_name(
        self, b2_app_data: ApplicationData, mock_b2_bucket: Mock, temp_test_file: Path
    ):
        """Test upload_file with empty B2 file name."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True
        bb._bucket = mock_b2_bucket

        with pytest.raises(ValueError) as exc_info:
            await bb.upload_file(str(temp_test_file), "")

        assert "B2 file name cannot be empty" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_upload_file_with_custom_info(
        self,
        b2_app_data: ApplicationData,
        mock_b2_api: Mock,
        mock_b2_bucket: Mock,
        temp_test_file: Path,
        mock_b2_file_version: Mock,
    ):
        """Test file upload with custom file info."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._b2_api = mock_b2_api
            bb._authorized = True
            bb._bucket = mock_b2_bucket

            file_info = UploadedFileInfo(scanned=True)

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                # First call gets bucket, second call uploads file
                mock_to_thread.side_effect = [mock_b2_bucket, mock_b2_file_version]
                result = await bb.upload_file(str(temp_test_file), "remote_file.txt", file_info)

                assert result == mock_b2_file_version

    @pytest.mark.anyio
    async def test_upload_file_failure(
        self,
        b2_app_data: ApplicationData,
        mock_b2_api: Mock,
        mock_b2_bucket: Mock,
        temp_test_file: Path,
    ):
        """Test upload_file failure."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._authorized = True
            bb._bucket = mock_b2_bucket

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.side_effect = Exception("Upload failed")

                with pytest.raises(B2FileOperationError) as exc_info:
                    await bb.upload_file(str(temp_test_file), "remote_file.txt")

                assert "Failed to upload file" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_get_download_url_by_name_success(
        self, b2_app_data: ApplicationData, mock_b2_api: Mock, mock_b2_bucket: Mock
    ):
        """Test successful download URL retrieval by name."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._b2_api = mock_b2_api
            bb._authorized = True
            bb._bucket = mock_b2_bucket

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                # First call gets bucket, second call gets download URL
                mock_to_thread.side_effect = [
                    mock_b2_bucket,
                    "https://example.com/download/file.txt",
                ]
                result = await bb.get_download_url_by_name("test_file.txt")

                assert result.download_url is not None

    @pytest.mark.anyio
    async def test_get_download_url_by_name_no_bucket(self, b2_app_data: ApplicationData):
        """Test get_download_url_by_name without bucket selection."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True

        with pytest.raises(B2BucketNotSelectedError):
            await bb.get_download_url_by_name("test_file.txt")

    @pytest.mark.anyio
    async def test_get_download_url_by_name_empty(
        self, b2_app_data: ApplicationData, mock_b2_bucket: Mock
    ):
        """Test get_download_url_by_name with empty file name."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True
        bb._bucket = mock_b2_bucket

        with pytest.raises(ValueError) as exc_info:
            await bb.get_download_url_by_name("")

        assert "File name cannot be empty" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_get_download_url_by_name_failure(
        self, b2_app_data: ApplicationData, mock_b2_api: Mock, mock_b2_bucket: Mock
    ):
        """Test get_download_url_by_name failure."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._authorized = True
            bb._bucket = mock_b2_bucket

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.side_effect = Exception("Failed to get URL")

                with pytest.raises(B2FileOperationError):
                    await bb.get_download_url_by_name("test_file.txt")

    @pytest.mark.anyio
    async def test_get_download_url_by_file_id_success(
        self, b2_app_data: ApplicationData, mock_b2_api: Mock, faker_instance: Faker
    ):
        """Test successful download URL retrieval by file ID."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._b2_api = mock_b2_api

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = "https://example.com/file"
                result = await bb.get_download_url_by_file_id(faker_instance.uuid4())

                assert result.download_url == "https://example.com/file"

    @pytest.mark.anyio
    async def test_get_download_url_by_file_id_empty(self, b2_app_data: ApplicationData):
        """Test get_download_url_by_file_id with empty file ID."""
        bb = BackBlaze(b2_app_data)

        with pytest.raises(ValueError) as exc_info:
            await bb.get_download_url_by_file_id("")

        assert "File ID cannot be empty" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_get_download_url_by_file_id_failure(
        self, b2_app_data: ApplicationData, mock_b2_api: Mock, faker_instance: Faker
    ):
        """Test get_download_url_by_file_id failure."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.side_effect = Exception("Failed")

                with pytest.raises(B2FileOperationError):
                    await bb.get_download_url_by_file_id(faker_instance.uuid4())

    @pytest.mark.anyio
    async def test_delete_file_success(
        self,
        b2_app_data: ApplicationData,
        mock_b2_api: Mock,
        mock_b2_bucket: Mock,
        faker_instance: Faker,
    ):
        """Test successful file deletion."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._b2_api = mock_b2_api
            bb._authorized = True
            bb._bucket = mock_b2_bucket

            mock_result = Mock(spec=FileIdAndName)

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = mock_result
                result = await bb.delete_file(faker_instance.uuid4(), "test_file.txt")

                assert result == mock_result

    @pytest.mark.anyio
    async def test_delete_file_no_bucket(self, b2_app_data: ApplicationData, faker_instance: Faker):
        """Test delete_file without bucket selection."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True

        with pytest.raises(B2BucketNotSelectedError):
            await bb.delete_file(faker_instance.uuid4(), "test_file.txt")

    @pytest.mark.anyio
    async def test_delete_file_empty_id(self, b2_app_data: ApplicationData, mock_b2_bucket: Mock):
        """Test delete_file with empty file ID."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True
        bb._bucket = mock_b2_bucket

        with pytest.raises(ValueError) as exc_info:
            await bb.delete_file("", "test_file.txt")

        assert "File ID and name cannot be empty" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_delete_file_empty_name(
        self, b2_app_data: ApplicationData, mock_b2_bucket: Mock, faker_instance: Faker
    ):
        """Test delete_file with empty file name."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True
        bb._bucket = mock_b2_bucket

        with pytest.raises(ValueError) as exc_info:
            await bb.delete_file(faker_instance.uuid4(), "")

        assert "File ID and name cannot be empty" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_delete_file_failure(
        self,
        b2_app_data: ApplicationData,
        mock_b2_api: Mock,
        mock_b2_bucket: Mock,
        faker_instance: Faker,
    ):
        """Test delete_file failure."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._authorized = True
            bb._bucket = mock_b2_bucket

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.side_effect = Exception("Deletion failed")

                with pytest.raises(B2FileOperationError):
                    await bb.delete_file(faker_instance.uuid4(), "test_file.txt")

    @pytest.mark.anyio
    async def test_get_temporary_download_link_success(
        self, b2_app_data: ApplicationData, mock_b2_bucket: Mock, faker_instance: Faker
    ):
        """Test successful temporary download link generation."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True
        bb._bucket = mock_b2_bucket

        file_id = faker_instance.uuid4()
        url = AnyUrl(f"https://example.com/file?fileId={file_id}")

        mock_file_info = Mock()
        mock_file_info.file_name = "test_file.txt"

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = [mock_file_info, "auth_token_123", "https://download.url"]
            result = await bb.get_temporary_download_link(url)

            assert result.auth_token == "auth_token_123"
            assert result.download_url == "https://download.url"

    @pytest.mark.anyio
    async def test_get_temporary_download_link_no_bucket(
        self, b2_app_data: ApplicationData, faker_instance: Faker
    ):
        """Test get_temporary_download_link without bucket selection."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True

        url = AnyUrl(f"https://example.com/file?fileId={faker_instance.uuid4()}")

        with pytest.raises(B2BucketNotSelectedError):
            await bb.get_temporary_download_link(url)

    @pytest.mark.anyio
    async def test_get_temporary_download_link_invalid_duration(
        self, b2_app_data: ApplicationData, mock_b2_bucket: Mock, faker_instance: Faker
    ):
        """Test get_temporary_download_link with invalid duration."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True
        bb._bucket = mock_b2_bucket

        url = AnyUrl(f"https://example.com/file?fileId={faker_instance.uuid4()}")

        with pytest.raises(ValueError) as exc_info:
            await bb.get_temporary_download_link(url, valid_duration_in_seconds=0)

        assert "Duration must be positive" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_get_temporary_download_link_no_file_id_in_url(
        self, b2_app_data: ApplicationData, mock_b2_bucket: Mock
    ):
        """Test get_temporary_download_link with URL missing fileId."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True
        bb._bucket = mock_b2_bucket

        url = AnyUrl("https://example.com/file")

        with pytest.raises(ValueError) as exc_info:
            await bb.get_temporary_download_link(url)

        assert "URL does not contain file ID parameter" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_get_temporary_download_link_failure(
        self, b2_app_data: ApplicationData, mock_b2_bucket: Mock, faker_instance: Faker
    ):
        """Test get_temporary_download_link failure."""
        bb = BackBlaze(b2_app_data)
        bb._authorized = True
        bb._bucket = mock_b2_bucket

        file_id = faker_instance.uuid4()
        url = AnyUrl(f"https://example.com/file?fileId={file_id}")

        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.side_effect = Exception("Failed")

            with pytest.raises(B2FileOperationError):
                await bb.get_temporary_download_link(url)

    @pytest.mark.anyio
    async def test_get_file_details_success(
        self,
        b2_app_data: ApplicationData,
        mock_b2_api: Mock,
        mock_b2_file_version: Mock,
        faker_instance: Faker,
    ):
        """Test successful file details retrieval."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)
            bb._b2_api = mock_b2_api

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = mock_b2_file_version
                result = await bb.get_file_details(faker_instance.uuid4())

                assert result == mock_b2_file_version

    @pytest.mark.anyio
    async def test_get_file_details_empty_id(self, b2_app_data: ApplicationData):
        """Test get_file_details with empty file ID."""
        bb = BackBlaze(b2_app_data)

        with pytest.raises(ValueError) as exc_info:
            await bb.get_file_details("")

        assert "File ID cannot be empty" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_get_file_details_failure(
        self, b2_app_data: ApplicationData, mock_b2_api: Mock, faker_instance: Faker
    ):
        """Test get_file_details failure."""
        with patch("app.services.back_blaze_b2.B2Api", return_value=mock_b2_api):
            bb = BackBlaze(b2_app_data)

            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.side_effect = Exception("Failed")

                with pytest.raises(B2FileOperationError):
                    await bb.get_file_details(faker_instance.uuid4())


class TestBackBlazeHelperMethods:
    """Test BackBlaze helper methods."""

    def test_validate_file_path_success(self, temp_test_file: Path):
        """Test _validate_file_path with valid file."""
        BackBlaze._validate_file_path(str(temp_test_file))

    def test_validate_file_path_empty(self):
        """Test _validate_file_path with empty path."""
        with pytest.raises(ValueError) as exc_info:
            BackBlaze._validate_file_path("")

        assert "File path cannot be empty" in str(exc_info.value)

    def test_validate_file_path_nonexistent(self):
        """Test _validate_file_path with nonexistent file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            BackBlaze._validate_file_path("/nonexistent/file.txt")

        assert "File not found" in str(exc_info.value)

    def test_cleanup_failed_upload(self, temp_test_file: Path):
        """Test _cleanup_failed_upload removes file."""
        assert temp_test_file.exists()
        BackBlaze._cleanup_failed_upload(str(temp_test_file))
        assert not temp_test_file.exists()

    def test_cleanup_failed_upload_nonexistent(self):
        """Test _cleanup_failed_upload with nonexistent file."""
        # Should not raise exception
        BackBlaze._cleanup_failed_upload("/nonexistent/file.txt")

    def test_extract_file_id_from_url_success(self, faker_instance: Faker):
        """Test _extract_file_id_from_url with valid URL."""
        file_id = faker_instance.uuid4()
        url = AnyUrl(f"https://example.com/file?fileId={file_id}")
        result = BackBlaze._extract_file_id_from_url(url)

        assert result == file_id

    def test_extract_file_id_from_url_no_file_id(self):
        """Test _extract_file_id_from_url with URL missing fileId."""
        url = AnyUrl("https://example.com/file")

        with pytest.raises(ValueError) as exc_info:
            BackBlaze._extract_file_id_from_url(url)

        assert "URL does not contain file ID parameter" in str(exc_info.value)
