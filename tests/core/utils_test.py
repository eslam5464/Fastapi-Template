import hashlib
import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request

from app.core.config import Environment, settings
from app.core.utils import (
    calculate_md5_hash,
    estimate_upload_time,
    get_client_ip,
    parse_user_id,
)


class TestParseUserId:
    """Test parse_user_id function."""

    def test_uuid_input_returns_uuid(self):
        """Test that UUID input returns UUID unchanged."""
        test_uuid = uuid.uuid4()

        result = parse_user_id(test_uuid)

        assert result == test_uuid
        assert isinstance(result, uuid.UUID)

    def test_string_uuid_converts_to_uuid(self):
        """Test that string representation of UUID converts to UUID."""
        test_uuid = uuid.uuid4()
        uuid_string = str(test_uuid)

        result = parse_user_id(uuid_string)

        assert result == test_uuid
        assert isinstance(result, uuid.UUID)

    def test_integer_converts_to_int(self):
        """Test that integer string converts to int."""
        user_id = "12345"

        result = parse_user_id(user_id)

        assert result == 12345
        assert isinstance(result, int)

    def test_integer_input_converts_to_int(self):
        """Test that integer input attempts UUID conversion first, then returns int."""
        user_id = 12345

        result = parse_user_id(user_id)

        # Will try UUID conversion first, fail, then try int (already int)
        assert isinstance(result, int)

    def test_invalid_string_returns_as_is(self):
        """Test that invalid string (not UUID, not int) returns unchanged."""
        user_id = "some-random-string"

        result = parse_user_id(user_id)

        assert result == user_id
        assert isinstance(result, str)

    def test_special_characters_string_returns_as_is(self):
        """Test that string with special characters returns unchanged."""
        user_id = "user@example.com"

        result = parse_user_id(user_id)

        assert result == user_id
        assert isinstance(result, str)


@pytest.mark.anyio
class TestGetClientIP:
    """Test get_client_ip function."""

    def test_local_environment_returns_localhost(self):
        """Test that local environment always returns localhost."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = MagicMock(host="192.168.1.1")

        with patch.object(settings, "current_environment", Environment.LOCAL):
            result = get_client_ip(request)

        assert result == "localhost"

    def test_x_forwarded_for_header(self):
        """Test X-Forwarded-For header extraction."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "203.0.113.195"}
        request.client = MagicMock(host="192.168.1.1")

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "203.0.113.195"

    def test_x_forwarded_for_multiple_ips(self):
        """Test X-Forwarded-For header with multiple IPs (takes first one)."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "203.0.113.195, 70.41.3.18, 150.172.238.178"}
        request.client = MagicMock(host="192.168.1.1")

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "203.0.113.195"

    def test_x_forwarded_for_with_spaces(self):
        """Test X-Forwarded-For header strips whitespace."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Forwarded-For": "  203.0.113.195  "}
        request.client = MagicMock(host="192.168.1.1")

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "203.0.113.195"

    def test_x_real_ip_header(self):
        """Test X-Real-IP header extraction."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Real-IP": "198.51.100.42"}
        request.client = MagicMock(host="192.168.1.1")

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "198.51.100.42"

    def test_x_real_ip_with_whitespace(self):
        """Test X-Real-IP header strips whitespace."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Real-IP": "  198.51.100.42  "}
        request.client = MagicMock(host="192.168.1.1")

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "198.51.100.42"

    def test_x_client_ip_header(self):
        """Test X-Client-IP header extraction."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Client-IP": "192.0.2.1"}
        request.client = MagicMock(host="192.168.1.1")

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "192.0.2.1"

    def test_x_client_ip_with_whitespace(self):
        """Test X-Client-IP header strips whitespace."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Client-IP": "  192.0.2.1  "}
        request.client = MagicMock(host="192.168.1.1")

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "192.0.2.1"

    def test_request_client_host_fallback(self):
        """Test fallback to request.client.host when no headers present."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = MagicMock(host="192.168.1.100")

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "192.168.1.100"

    def test_unknown_when_no_client(self):
        """Test returns 'unknown' when request.client is None."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.client = None

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "unknown"

    def test_header_priority_x_forwarded_for_first(self):
        """Test that X-Forwarded-For has highest priority."""
        request = MagicMock(spec=Request)
        request.headers = {
            "X-Forwarded-For": "203.0.113.195",
            "X-Real-IP": "198.51.100.42",
            "X-Client-IP": "192.0.2.1",
        }
        request.client = MagicMock(host="192.168.1.1")

        with patch.object(settings, "current_environment", Environment.PRD):
            result = get_client_ip(request)

        assert result == "203.0.113.195"


@pytest.mark.anyio
class TestCalculateMd5Hash:
    """Test calculate_md5_hash function."""

    async def test_file_not_found_raises_error(self):
        """Test that FileNotFoundError is raised for non-existent file."""
        non_existent_path = "/path/to/nonexistent/file.txt"

        with pytest.raises(FileNotFoundError, match="File not found"):
            await calculate_md5_hash(non_existent_path)

    async def test_directory_raises_error(self):
        """Test that FileNotFoundError is raised for directory path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError, match="File not found"):
                await calculate_md5_hash(tmpdir)

    async def test_calculates_hash_for_small_file(self):
        """Test MD5 hash calculation for small file."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tmp_file:
            content = b"Hello, World!"
            tmp_file.write(content)
            tmp_file.flush()
            file_path = tmp_file.name

        try:
            result = await calculate_md5_hash(file_path)

            # Calculate expected hash
            expected_hash = hashlib.md5(content).hexdigest()
            assert result == expected_hash
        finally:
            Path(file_path).unlink()

    async def test_calculates_hash_for_large_file(self):
        """Test MD5 hash calculation for file larger than chunk size."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tmp_file:
            # Create 10KB file (larger than 4096 byte chunk)
            content = b"x" * (10 * 1024)
            tmp_file.write(content)
            tmp_file.flush()
            file_path = tmp_file.name

        try:
            result = await calculate_md5_hash(file_path)

            # Calculate expected hash
            expected_hash = hashlib.md5(content).hexdigest()
            assert result == expected_hash
        finally:
            Path(file_path).unlink()

    async def test_kb_file_size_display(self):
        """Test that KB size is logged correctly for files < 1MB."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tmp_file:
            # Create 500 KB file
            content = b"x" * (500 * 1024)
            tmp_file.write(content)
            tmp_file.flush()
            file_path = tmp_file.name

        try:
            with patch("app.core.utils.logger") as mock_logger:
                await calculate_md5_hash(file_path)

                # Check that logger.info was called with KB in message
                mock_logger.info.assert_called_once()
                log_message = mock_logger.info.call_args[0][0]
                assert "KB" in log_message
        finally:
            Path(file_path).unlink()

    async def test_mb_file_size_display(self):
        """Test that MB size is logged correctly for files >= 1MB and < 1GB."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tmp_file:
            # Create 2 MB file
            content = b"x" * (2 * 1024 * 1024)
            tmp_file.write(content)
            tmp_file.flush()
            file_path = tmp_file.name

        try:
            with patch("app.core.utils.logger") as mock_logger:
                await calculate_md5_hash(file_path)

                # Check that logger.info was called with MB in message
                mock_logger.info.assert_called_once()
                log_message = mock_logger.info.call_args[0][0]
                assert "MB" in log_message
        finally:
            Path(file_path).unlink()

    async def test_gb_file_size_display(self):
        """Test that GB size is logged correctly for files >= 1GB."""
        # Mock the file size instead of creating 1GB file
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tmp_file:
            content = b"test"
            tmp_file.write(content)
            tmp_file.flush()
            file_path = tmp_file.name

        try:
            # Mock Path.stat to return 1GB size and is_file to return True
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value = MagicMock(st_size=1024 * 1024 * 1024)
                with patch("pathlib.Path.is_file", return_value=True):
                    with patch("app.core.utils.logger") as mock_logger:
                        await calculate_md5_hash(file_path)

                        # Check that logger.info was called with GB in message
                        mock_logger.info.assert_called_once()
                        log_message = mock_logger.info.call_args[0][0]
                        assert "GB" in log_message
        finally:
            Path(file_path).unlink()

    async def test_empty_file(self):
        """Test MD5 hash calculation for empty file."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tmp_file:
            file_path = tmp_file.name

        try:
            result = await calculate_md5_hash(file_path)

            # MD5 of empty file
            expected_hash = hashlib.md5(b"").hexdigest()
            assert result == expected_hash
        finally:
            Path(file_path).unlink()

    async def test_path_object_input(self):
        """Test that Path object can be used as input."""
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tmp_file:
            content = b"Test with Path object"
            tmp_file.write(content)
            tmp_file.flush()
            file_path = Path(tmp_file.name)

        try:
            result = await calculate_md5_hash(file_path)

            expected_hash = hashlib.md5(content).hexdigest()
            assert result == expected_hash
        finally:
            file_path.unlink()


@pytest.mark.anyio
class TestEstimateUploadTime:
    """Test estimate_upload_time function."""

    async def test_https_url_default_port(self):
        """Test HTTPS URL construction with default port 443."""
        mock_response = AsyncMock()
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None

        with patch("aiohttp.ClientSession.post", return_value=mock_response) as mock_post:
            with patch("time.time", side_effect=[0.0, 1.0]):  # 1 second upload
                result = await estimate_upload_time(
                    url="example.com", path="/upload", port=443, file_size_mb=1
                )

                # Should construct https://example.com/upload
                mock_post.assert_called_once()
                call_kwargs = mock_post.call_args[1]
                assert call_kwargs["url"] == "https://example.com/upload"

    async def test_http_url_default_port(self):
        """Test HTTP URL construction with default port 80."""
        mock_response = AsyncMock()
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None

        with patch("aiohttp.ClientSession.post", return_value=mock_response) as mock_post:
            with patch("time.time", side_effect=[0.0, 1.0]):
                result = await estimate_upload_time(
                    url="example.com", path="/upload", port=80, file_size_mb=1
                )

                # Should construct http://example.com/upload
                mock_post.assert_called_once()
                call_kwargs = mock_post.call_args[1]
                assert call_kwargs["url"] == "http://example.com/upload"

    async def test_custom_port(self):
        """Test URL construction with custom port."""
        mock_response = AsyncMock()
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None

        with patch("aiohttp.ClientSession.post", return_value=mock_response) as mock_post:
            with patch("time.time", side_effect=[0.0, 1.0]):
                result = await estimate_upload_time(
                    url="example.com", path="/upload", port=8080, file_size_mb=1
                )

                # Should construct http://example.com:8080/upload
                mock_post.assert_called_once()
                call_kwargs = mock_post.call_args[1]
                assert call_kwargs["url"] == "http://example.com:8080/upload"

    async def test_custom_https_port(self):
        """Test HTTPS URL construction with custom port."""
        mock_response = AsyncMock()
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None

        with patch("aiohttp.ClientSession.post", return_value=mock_response) as mock_post:
            with patch("time.time", side_effect=[0.0, 1.0]):
                result = await estimate_upload_time(
                    url="example.com", path="/upload", port=8443, file_size_mb=1
                )

                # Should construct http://example.com:8443/upload (8443 is not 443, so it uses http)
                mock_post.assert_called_once()
                call_kwargs = mock_post.call_args[1]
                assert call_kwargs["url"] == "http://example.com:8443/upload"

    async def test_url_with_https_protocol(self):
        """Test URL that already has https:// protocol."""
        mock_response = AsyncMock()
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None

        with patch("aiohttp.ClientSession.post", return_value=mock_response) as mock_post:
            with patch("time.time", side_effect=[0.0, 1.0]):
                result = await estimate_upload_time(
                    url="https://example.com", path="/upload", port=443, file_size_mb=1
                )

                # Should use URL as-is with path
                mock_post.assert_called_once()
                call_kwargs = mock_post.call_args[1]
                assert call_kwargs["url"] == "https://example.com/upload"

    async def test_url_with_http_protocol(self):
        """Test URL that already has http:// protocol."""
        mock_response = AsyncMock()
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None

        with patch("aiohttp.ClientSession.post", return_value=mock_response) as mock_post:
            with patch("time.time", side_effect=[0.0, 1.0]):
                result = await estimate_upload_time(
                    url="http://example.com", path="/upload", port=80, file_size_mb=1
                )

                # Should use URL as-is with path
                mock_post.assert_called_once()
                call_kwargs = mock_post.call_args[1]
                assert call_kwargs["url"] == "http://example.com/upload"

    async def test_calculates_upload_time(self):
        """Test upload time calculation based on speed."""
        mock_response = AsyncMock()
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None

        with patch("aiohttp.ClientSession.post", return_value=mock_response):
            # Simulate 0.5 second upload (2 MB/s speed)
            with patch("time.time", side_effect=[0.0, 0.5]):
                result = await estimate_upload_time(
                    url="example.com", path="/upload", port=443, file_size_mb=10  # 10 MB file
                )

                # Upload speed: 1 MB / 0.5s = 2 MB/s
                # Time for 10 MB: 10 / 2 = 5 seconds
                assert result == 5.0

    async def test_sends_correct_data_and_headers(self):
        """Test that correct data and headers are sent."""
        mock_response = AsyncMock()
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None

        with patch("aiohttp.ClientSession.post", return_value=mock_response) as mock_post:
            with patch("time.time", side_effect=[0.0, 1.0]):
                await estimate_upload_time()

                # Check data and headers
                call_kwargs = mock_post.call_args[1]
                assert call_kwargs["headers"]["Content-Type"] == "application/octet-stream"
                assert len(call_kwargs["data"]) == 1024 * 1024  # 1 MB
