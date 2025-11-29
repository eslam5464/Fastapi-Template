from io import BytesIO
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio
from b2sdk._internal.bucket import Bucket
from b2sdk._internal.file_version import FileVersion
from b2sdk.v2 import B2Api
from faker import Faker
from firebase_admin import App
from firebase_admin.auth import ListUsersPage, UserRecord
from firebase_admin.credentials import Certificate
from firebase_admin.messaging import BatchResponse, SendResponse
from gcloud.aio.storage import Bucket as GCSBucket, Storage
from google.cloud.firestore import AsyncClient
from redis.asyncio import ConnectionPool, Redis

from app.core.config import Environment
from app.schemas import (
    ApplicationData,
    BucketFile,
    BucketFolder,
    FirebaseServiceAccount,
    ServiceAccount,
)


@pytest.fixture
def faker_instance() -> Faker:
    """Create a Faker instance for test data generation."""
    return Faker()


# ==================== BackBlaze B2 Fixtures ====================


@pytest.fixture
def b2_app_data(faker_instance: Faker) -> ApplicationData:
    """Create mock BackBlaze application data."""
    return ApplicationData(
        app_id=faker_instance.uuid4(),
        app_key=faker_instance.sha256(),
    )


@pytest.fixture
def mock_b2_api() -> Mock:
    """Create a mock B2Api instance."""
    mock_api = Mock(spec=B2Api)
    mock_api.authorize_account = Mock()
    mock_api.get_bucket_by_name = Mock()
    mock_api.list_buckets = Mock()
    mock_api.create_bucket = Mock()
    mock_api.delete_bucket = Mock()
    mock_api.delete_file_version = Mock()
    mock_api.get_file_info = Mock()
    mock_api.get_download_url_for_fileid = Mock()
    return mock_api


@pytest.fixture
def mock_b2_bucket(faker_instance: Faker) -> Mock:
    """Create a mock B2 Bucket instance."""
    mock_bucket = Mock(spec=Bucket)
    mock_bucket.name = faker_instance.word()
    mock_bucket.id_ = faker_instance.uuid4()
    mock_bucket.upload_local_file = Mock()
    mock_bucket.get_download_url = Mock(return_value=f"https://example.com/{faker_instance.word()}")
    mock_bucket.get_file_info_by_id = Mock()
    mock_bucket.get_download_authorization = Mock(return_value=faker_instance.sha256())
    mock_bucket.update = Mock()
    return mock_bucket


@pytest.fixture
def mock_b2_file_version(faker_instance: Faker) -> Mock:
    """Create a mock FileVersion instance."""
    mock_file = Mock(spec=FileVersion)
    mock_file.id_ = faker_instance.uuid4()
    mock_file.file_name = faker_instance.file_name()
    mock_file.size = faker_instance.random_int(min=100, max=10000)
    return mock_file


@pytest.fixture
def initialized_backblaze(b2_app_data: ApplicationData, mock_b2_api: Mock):
    """Create a BackBlaze instance with properly initialized _b2_api."""
    from app.services.back_blaze_b2 import BackBlaze

    bb = BackBlaze(b2_app_data)
    bb._b2_api = mock_b2_api
    return bb


@pytest.fixture
def temp_test_file(tmp_path: Path, faker_instance: Faker) -> Path:
    """Create a temporary test file."""
    test_file = tmp_path / "test_file.txt"
    test_file.write_text(faker_instance.text())
    return test_file


# ==================== Firebase Fixtures ====================


@pytest.fixture
def firebase_service_account(faker_instance: Faker) -> FirebaseServiceAccount:
    """Create mock Firebase service account credentials."""
    return FirebaseServiceAccount(
        type="service_account",
        project_id=faker_instance.word(),
        private_key_id=faker_instance.uuid4(),
        private_key=f"-----BEGIN ##$$##-----\n{faker_instance.sha256()}\n-----END ##$$##-----".replace(
            "##$$##", "PRIVATE KEY"
        ),
        client_email=faker_instance.email(),
        client_id=faker_instance.uuid4(),
        auth_uri="https://accounts.google.com/o/oauth2/auth",
        token_uri="https://oauth2.googleapis.com/token",
        auth_provider_x509_cert_url="https://www.googleapis.com/oauth2/v1/certs",
        client_x509_cert_url=faker_instance.url(),
        universe_domain="googleapis.com",
    )


@pytest.fixture
def mock_firebase_app() -> Mock:
    """Create a mock Firebase App instance."""
    return Mock(spec=App)


@pytest.fixture
def mock_firebase_certificate() -> Mock:
    """Create a mock Firebase Certificate."""
    return Mock(spec=Certificate)


@pytest.fixture
def mock_user_record(faker_instance: Faker) -> Mock:
    """Create a mock Firebase UserRecord."""
    mock_user = Mock(spec=UserRecord)
    mock_user.uid = faker_instance.uuid4()
    mock_user.email = faker_instance.email()
    mock_user.display_name = faker_instance.name()
    mock_user.phone_number = faker_instance.phone_number()
    return mock_user


@pytest.fixture
def mock_list_users_page() -> Mock:
    """Create a mock ListUsersPage."""
    return Mock(spec=ListUsersPage)


@pytest.fixture
def mock_batch_response() -> Mock:
    """Create a mock BatchResponse for FCM."""
    mock_response = Mock(spec=BatchResponse)
    mock_response.success_count = 5
    mock_response.failure_count = 0
    mock_response.responses = [Mock(spec=SendResponse, success=True) for _ in range(5)]
    return mock_response


# ==================== Firestore Fixtures ====================


@pytest.fixture
def mock_firestore_client() -> Mock:
    """Create a mock Firestore AsyncClient."""
    return Mock(spec=AsyncClient)


@pytest.fixture
def mock_firestore_collection() -> Mock:
    """Create a mock Firestore collection reference."""
    mock_collection = Mock()
    mock_collection.document = Mock()
    mock_collection.stream = AsyncMock()
    return mock_collection


@pytest.fixture
def mock_firestore_document() -> Mock:
    """Create a mock Firestore document reference."""
    mock_doc = Mock()
    mock_doc.set = AsyncMock()
    mock_doc.update = AsyncMock()
    mock_doc.delete = AsyncMock()
    mock_doc.get = AsyncMock()
    return mock_doc


# ==================== GCS Fixtures ====================


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


# ==================== Redis/Cache Fixtures ====================


@pytest.fixture
def mock_redis_client() -> AsyncMock:
    """Create a mock Redis client."""
    mock_redis = AsyncMock(spec=Redis)
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock()
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)
    mock_redis.keys = AsyncMock(return_value=[])
    mock_redis.exists = AsyncMock(return_value=1)
    mock_redis.pipeline = Mock()
    mock_redis.close = AsyncMock()

    # Setup pipeline mock
    mock_pipeline = AsyncMock()
    mock_pipeline.zremrangebyscore = Mock(return_value=mock_pipeline)
    mock_pipeline.zadd = Mock(return_value=mock_pipeline)
    mock_pipeline.zcard = Mock(return_value=mock_pipeline)
    mock_pipeline.expire = Mock(return_value=mock_pipeline)
    mock_pipeline.execute = AsyncMock(return_value=[0, 1, 5, True])
    mock_redis.pipeline.return_value = mock_pipeline

    return mock_redis


@pytest.fixture
def mock_redis_pool() -> Mock:
    """Create a mock Redis ConnectionPool."""
    mock_pool = Mock(spec=ConnectionPool)
    mock_pool.connection_kwargs = {"protocol": "2"}
    return mock_pool


@pytest.fixture
def patched_cache_environment(mock_redis_client, mock_redis_pool):
    """Patch environment for cache tests."""
    with patch("app.services.cache.base.get_redis_pool", return_value=mock_redis_pool):
        with patch("app.services.cache.base.settings.current_environment", Environment.LOCAL):
            with patch("app.services.cache.base.Redis", return_value=mock_redis_client):
                yield


# ==================== Helper Fixtures ====================


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


@pytest.fixture
def sample_bucket_folder(faker_instance: Faker) -> BucketFolder:
    """Create a sample BucketFolder."""
    return BucketFolder(
        name=faker_instance.word(),
        bucket_folder_path=f"{faker_instance.word()}/",
    )


@pytest_asyncio.fixture
async def async_temp_file(tmp_path: Path, faker_instance: Faker) -> AsyncGenerator[Path, None]:
    """Create a temporary file that gets cleaned up."""
    test_file = tmp_path / f"test_{faker_instance.uuid4()}.txt"
    test_file.write_text(faker_instance.text())
    yield test_file
    if test_file.exists():
        test_file.unlink()
