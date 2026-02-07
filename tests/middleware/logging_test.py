from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request
from starlette.middleware.base import _StreamingResponse

from app.middleware.logging import LoggingMiddleware


@pytest.mark.anyio
class TestLoggingMiddleware:
    """Test LoggingMiddleware functionality."""

    async def test_generates_request_id(self):
        """Test that middleware generates request ID."""
        middleware = LoggingMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.method = "GET"
        request.url = MagicMock(path="/test")
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {"user-agent": "test-agent"}

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.logging.logger"):
            await middleware.dispatch(request, call_next)

            # Request ID should be generated and stored in state
            assert hasattr(request.state, "request_id")
            assert isinstance(request.state.request_id, str)
            assert len(request.state.request_id) == 8

    async def test_logs_successful_request(self):
        """Test that successful requests are logged."""
        middleware = LoggingMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.method = "POST"
        request.url = MagicMock(path="/api/test")
        request.client = MagicMock(host="10.0.0.1")
        request.headers = {"user-agent": "Mozilla/5.0"}

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 201
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.logging.logger") as mock_logger:
            await middleware.dispatch(request, call_next)

            # Should log twice: request and response
            assert mock_logger.trace.call_count == 2

            # Check request log
            first_call = mock_logger.trace.call_args_list[0]
            assert "POST" in first_call[0][0]
            assert "/api/test" in first_call[0][0]
            assert "10.0.0.1" in first_call[0][0]

            # Check response log
            second_call = mock_logger.trace.call_args_list[1]
            assert "201" in second_call[0][0]
            assert "Time:" in second_call[0][0]

    async def test_adds_request_id_to_response(self):
        """Test that X-Request-ID header is added to response."""
        middleware = LoggingMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.method = "GET"
        request.url = MagicMock(path="/test")
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {"user-agent": "test"}

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.logging.logger"):
            await middleware.dispatch(request, call_next)

            # X-Request-ID header should be added
            assert "X-Request-ID" in response.headers
            assert response.headers["X-Request-ID"] == request.state.request_id

    async def test_logs_error_with_details(self):
        """Test that errors are logged with request details."""
        middleware = LoggingMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.method = "POST"
        request.url = MagicMock(path="/api/error")
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {"user-agent": "test"}
        request.query_params = {"param": "value"}
        request.path_params = {"id": "123"}

        # Mock json() to return data
        async def mock_json():
            return {"key": "value"}

        request.json = mock_json

        test_error = ValueError("Test error")

        async def call_next(req):
            raise test_error

        with patch("app.middleware.logging.logger") as mock_logger:
            with pytest.raises(ValueError):
                await middleware.dispatch(request, call_next)

            # Should log error
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args

            # Check error log contains details
            assert "Test error" in error_call[0][0]
            assert "POST" in error_call[0][0]
            assert "/api/error" in error_call[0][0]

            # Check keyword args
            assert (
                "request_body" in error_call[1]
            ), f"Expected 'request_body' in log kwargs, got {error_call[1].keys()}"
            assert error_call[1]["request_body"] == {"key": "value"}
            assert error_call[1]["request_query_params"] == {"param": "value"}
            assert error_call[1]["request_path_params"] == {"id": "123"}

    async def test_handles_json_parse_error(self):
        """Test that JSON parse errors are handled gracefully."""
        middleware = LoggingMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.method = "POST"
        request.url = MagicMock(path="/api/test")
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {"user-agent": "test"}
        request.query_params = {}
        request.path_params = {}

        # Mock json() to raise exception
        async def mock_json():
            raise ValueError("Invalid JSON")

        request.json = mock_json

        async def call_next(req):
            raise RuntimeError("Some error")

        with patch("app.middleware.logging.logger") as mock_logger:
            with pytest.raises(RuntimeError):
                await middleware.dispatch(request, call_next)

            # Should log error with empty string for body
            mock_logger.error.assert_called_once()
            error_call = mock_logger.error.call_args
            assert error_call[1]["request_body"] == ""

    async def test_missing_user_agent(self):
        """Test handling of missing User-Agent header."""
        middleware = LoggingMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.method = "GET"
        request.url = MagicMock(path="/test")
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {}  # No user-agent

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.logging.logger") as mock_logger:
            await middleware.dispatch(request, call_next)

            # Should log with 'unknown' user agent
            first_call = mock_logger.trace.call_args_list[0]
            assert "unknown" in first_call[0][0]

    async def test_missing_client(self):
        """Test handling when request.client is None."""
        middleware = LoggingMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.method = "GET"
        request.url = MagicMock(path="/test")
        request.client = None  # No client
        request.headers = {"user-agent": "test"}

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            return response

        with patch("app.middleware.logging.logger") as mock_logger:
            await middleware.dispatch(request, call_next)

            # Should log with 'unknown' client IP
            first_call = mock_logger.trace.call_args_list[0]
            assert "unknown" in first_call[0][0]

    async def test_measures_processing_time(self):
        """Test that processing time is measured and logged."""
        middleware = LoggingMiddleware(MagicMock())
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.method = "GET"
        request.url = MagicMock(path="/test")
        request.client = MagicMock(host="192.168.1.1")
        request.headers = {"user-agent": "test"}

        response = MagicMock(spec=_StreamingResponse)
        response.status_code = 200
        response.headers = {}

        async def call_next(req):
            await asyncio.sleep(0.1)  # Simulate processing time
            return response

        import asyncio

        with patch("app.middleware.logging.logger") as mock_logger:
            await middleware.dispatch(request, call_next)

            # Check that time is logged in response
            second_call = mock_logger.trace.call_args_list[1]
            assert "Time:" in second_call[0][0]
            assert "s" in second_call[0][0]
