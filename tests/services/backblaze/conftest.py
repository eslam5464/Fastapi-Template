"""BackBlaze B2 fixtures."""

from unittest.mock import Mock

import pytest
from b2sdk._internal.bucket import Bucket
from b2sdk._internal.file_version import FileVersion
from b2sdk.v2 import B2Api
from faker import Faker

from app.schemas import ApplicationData


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
