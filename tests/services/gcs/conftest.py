"""Google Cloud Storage fixtures."""

from io import BytesIO
from unittest.mock import AsyncMock, Mock

import pytest
from faker import Faker
from gcloud.aio.storage import Bucket as GCSBucket
from gcloud.aio.storage import Storage

from app.schemas import BucketFile, ServiceAccount


@pytest.fixture
def gcs_service_account(faker_instance: Faker) -> ServiceAccount:
    """Create mock GCS service account credentials."""
    return ServiceAccount(
        project_id=faker_instance.word(),
        private_key_id=faker_instance.uuid4(),
        private_key=f"-----BEGIN ##$$##-----\n{faker_instance.sha256()}\n-----END ##$$##-----".replace(
            "##$$##", "PRIVATE KEY"
        ),
        client_email=faker_instance.email(),
        client_id=faker_instance.uuid4(),
    )


@pytest.fixture
def mock_gcs_storage() -> AsyncMock:
    """Create a mock GCS Storage instance."""
    mock_storage = AsyncMock(spec=Storage)
    mock_storage.list_buckets = AsyncMock()
    mock_storage.upload = AsyncMock()
    mock_storage.download = AsyncMock()
    mock_storage.download_metadata = AsyncMock()
    mock_storage.list_objects = AsyncMock()
    mock_storage.delete = AsyncMock()
    mock_storage.copy = AsyncMock()
    mock_storage.close = AsyncMock()
    return mock_storage


@pytest.fixture
def mock_gcs_bucket() -> Mock:
    """Create a mock GCS Bucket instance."""
    return Mock(spec=GCSBucket)


@pytest.fixture
def sample_file_bytes(faker_instance: Faker) -> BytesIO:
    """Create a sample BytesIO file."""
    content = faker_instance.text().encode()
    return BytesIO(content)


@pytest.fixture
def sample_bucket_file(faker_instance: Faker) -> BucketFile:
    """Create a sample BucketFile."""
    bucket_data = {
        "id": faker_instance.uuid4(),
        "basename": faker_instance.file_name(),
        "extension": ".txt",
        "file_path_in_bucket": f"folder/{faker_instance.file_name()}",
        "bucket_name": faker_instance.word(),
        "public_url": f"https://storage.googleapis.com/{faker_instance.word()}/file.txt",
        "authenticated_url": f"https://storage.cloud.google.com/{faker_instance.word()}/file.txt",
        "size_bytes": faker_instance.random_int(min=100, max=10000),
        "creation_date": faker_instance.date_time(),
        "modification_date": faker_instance.date_time(),
        "content_type": "text/plain",
        "metadata": {},
        "md5_hash": faker_instance.md5(),
        "crc32c_checksum": "AAAAAA==",
    }

    return BucketFile.model_validate(bucket_data)
