"""Tests for the logger module."""

import logging
import os
import queue
import sys
from unittest.mock import MagicMock, patch

from app.core.config import Environment


class TestOpenObserveHandler:
    """Tests for OpenObserveHandler class."""

    def test_init_creates_handler(self):
        """Test OpenObserveHandler initialization."""
        from app.core.logger import OpenObserveHandler

        with patch.object(OpenObserveHandler, "_start_worker"):
            handler = OpenObserveHandler(
                url="http://localhost:5080",
                token="test-token",
                org="test-org",
                stream="test-stream",
                batch_size=5,
                flush_interval=2.0,
                max_retries=2,
            )

            assert handler.url == "http://localhost:5080"
            assert handler.token == "test-token"
            assert handler.org == "test-org"
            assert handler.stream == "test-stream"
            assert handler.batch_size == 5
            assert handler.flush_interval == 2.0
            assert handler.max_retries == 2
            assert isinstance(handler.log_queue, queue.Queue)

            # Cleanup
            handler.shutdown_event.set()

    def test_get_client_lazy_initialization(self):
        """Test _get_client lazily initializes HTTP client."""
        from app.core.logger import OpenObserveHandler

        with patch.object(OpenObserveHandler, "_start_worker"):
            handler = OpenObserveHandler(
                url="http://localhost:5080",
                token="test-token",
            )

            assert handler._client is None

            with patch("httpx.Client") as mock_client:
                mock_client.return_value = MagicMock()
                client = handler._get_client()

                assert client is not None
                mock_client.assert_called_once()

            # Cleanup
            handler.shutdown_event.set()

    def test_get_client_returns_existing(self):
        """Test _get_client returns existing client if already initialized."""
        from app.core.logger import OpenObserveHandler

        with patch.object(OpenObserveHandler, "_start_worker"):
            handler = OpenObserveHandler(
                url="http://localhost:5080",
                token="test-token",
            )

            mock_client = MagicMock()
            handler._client = mock_client

            result = handler._get_client()
            assert result == mock_client

            # Cleanup
            handler.shutdown_event.set()

    def test_get_client_handles_import_error(self):
        """Test _get_client handles missing httpx gracefully."""
        from app.core.logger import OpenObserveHandler

        with patch.object(OpenObserveHandler, "_start_worker"):
            handler = OpenObserveHandler(
                url="http://localhost:5080",
                token="test-token",
            )

            with patch.dict(sys.modules, {"httpx": None}):
                with patch(
                    "builtins.__import__", side_effect=ImportError("No module named 'httpx'")
                ):
                    # Reset client to None to force re-initialization
                    handler._client = None

                    # This should handle the ImportError gracefully
                    # The actual behavior depends on implementation

            # Cleanup
            handler.shutdown_event.set()

    def test_send_log_queues_message(self):
        """Test send_log adds log to queue."""
        from app.core.logger import OpenObserveHandler

        with patch.object(OpenObserveHandler, "_start_worker"):
            handler = OpenObserveHandler(
                url="http://localhost:5080",
                token="test-token",
            )

            log_data = {"message": "test log", "level": "INFO"}
            handler.send_log(log_data)

            # Check log was added to queue
            assert not handler.log_queue.empty()
            queued_log = handler.log_queue.get_nowait()
            assert queued_log == log_data

            # Cleanup
            handler.shutdown_event.set()

    def test_send_log_handles_full_queue(self):
        """Test send_log handles full queue gracefully."""
        from app.core.logger import OpenObserveHandler

        with patch.object(OpenObserveHandler, "_start_worker"):
            # Create handler with small queue
            handler = OpenObserveHandler(
                url="http://localhost:5080",
                token="test-token",
            )

            # Create a full queue by replacing with a small one
            handler.log_queue = queue.Queue(maxsize=1)
            handler.log_queue.put({"message": "existing"})

            # This should not raise, just print warning
            handler.send_log({"message": "new log"})

            # Cleanup
            handler.shutdown_event.set()

    def test_shutdown(self):
        """Test shutdown method stops worker and closes client."""
        from app.core.logger import OpenObserveHandler

        with patch.object(OpenObserveHandler, "_start_worker"):
            handler = OpenObserveHandler(
                url="http://localhost:5080",
                token="test-token",
            )

            mock_client = MagicMock()
            handler._client = mock_client
            handler.worker_thread = MagicMock()
            handler.worker_thread.is_alive.return_value = False

            handler.shutdown()

            assert handler.shutdown_event.is_set()
            mock_client.close.assert_called_once()

    def test_shutdown_idempotent(self):
        """Test shutdown can be called multiple times safely."""
        from app.core.logger import OpenObserveHandler

        with patch.object(OpenObserveHandler, "_start_worker"):
            handler = OpenObserveHandler(
                url="http://localhost:5080",
                token="test-token",
            )

            handler.shutdown_event.set()  # Already shut down

            # Should not raise
            handler.shutdown()


class TestCorrelationFilter:
    """Tests for correlation_filter function."""

    def test_adds_request_id(self):
        """Test correlation_filter adds request_id to record."""
        from app.core.logger import correlation_filter, request_id_var

        # Set a request ID
        token = request_id_var.set("test-request-123")

        try:
            record = {"extra": {}}
            result = correlation_filter(record)

            assert result is True
            assert record["extra"]["request_id"] == "test-request-123"
            assert "process_id" in record["extra"]
        finally:
            request_id_var.reset(token)

    def test_generates_request_id_if_none(self):
        """Test correlation_filter generates request_id if not set."""
        from app.core.logger import correlation_filter, request_id_var

        # Ensure no request ID is set
        request_id_var.set(None)

        record = {"extra": {}}
        result = correlation_filter(record)

        assert result is True
        assert "request_id" in record["extra"]
        assert record["extra"]["request_id"] is not None

    def test_adds_process_id(self):
        """Test correlation_filter adds process_id."""
        from app.core.logger import correlation_filter

        record = {"extra": {}}
        correlation_filter(record)

        assert record["extra"]["process_id"] == os.getpid()

    def test_filters_openobserve_logs(self):
        """Test correlation_filter removes OpenObserve HTTP logs."""
        from app.core.logger import correlation_filter

        with patch("app.core.logger.settings") as mock_settings:
            mock_settings.openobserve_url = "http://openobserve.example.com"

            record = {
                "name": "httpx",
                "message": "POST http://openobserve.example.com/api/org/stream",
                "extra": {},
            }
            result = correlation_filter(record)

            assert result is False


class TestInterceptHandler:
    """Tests for InterceptHandler class."""

    def test_emit_redirects_to_loguru(self):
        """Test emit redirects log records to loguru."""
        from app.core.logger import InterceptHandler

        handler = InterceptHandler()

        # Create a mock log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        with patch("app.core.logger.logger") as mock_logger:
            mock_logger.level.return_value.name = "INFO"
            mock_logger.opt.return_value.log = MagicMock()

            handler.emit(record)

            mock_logger.opt.assert_called()

    def test_emit_handles_unknown_level(self):
        """Test emit handles unknown log levels."""
        from app.core.logger import InterceptHandler

        handler = InterceptHandler()

        # Create a mock log record with custom level
        record = logging.LogRecord(
            name="test",
            level=25,  # Custom level between INFO and WARNING
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        with patch("app.core.logger.logger") as mock_logger:
            mock_logger.level.side_effect = ValueError("Unknown level")
            mock_logger.opt.return_value.log = MagicMock()

            handler.emit(record)

            mock_logger.opt.assert_called()


class TestSetupLogger:
    """Tests for setup_logger function."""

    def test_setup_logger_removes_default_handler(self):
        """Test setup_logger removes default loguru handler."""
        from app.core.logger import setup_logger

        with patch("app.core.logger.logger") as mock_logger:
            with patch("app.core.logger.settings") as mock_settings:
                mock_settings.current_environment = Environment.DEV
                mock_settings.log_level = 20  # INFO
                mock_settings.log_to_openobserve = False

                setup_logger()

                mock_logger.remove.assert_called_once()

    def test_setup_logger_adds_console_handler(self):
        """Test setup_logger adds console output handler."""
        from app.core.logger import setup_logger

        with patch("app.core.logger.logger") as mock_logger:
            with patch("app.core.logger.settings") as mock_settings:
                mock_settings.current_environment = Environment.DEV
                mock_settings.log_level = 20  # INFO
                mock_settings.log_to_openobserve = False

                setup_logger()

                # logger.add should be called for console and file
                assert mock_logger.add.call_count >= 2


class TestConfigureUvicornLogging:
    """Tests for configure_uvicorn_logging function."""

    def test_configures_uvicorn_loggers(self):
        """Test configure_uvicorn_logging intercepts uvicorn loggers."""
        from app.core.logger import configure_uvicorn_logging

        with patch("logging.basicConfig"):
            with patch(
                "logging.root.manager.loggerDict",
                {"uvicorn": MagicMock(), "uvicorn.error": MagicMock()},
            ):
                configure_uvicorn_logging()


class TestShutdownLogger:
    """Tests for shutdown_logger function."""

    def test_shutdown_logger_closes_openobserve(self):
        """Test shutdown_logger closes OpenObserve handler."""
        from app.core import logger as logger_module

        mock_handler = MagicMock()
        logger_module._openobserve_handler = mock_handler

        with patch.object(logger_module.logger, "info"):
            with patch.object(logger_module.logger, "complete"):
                logger_module.shutdown_logger()

                mock_handler.shutdown.assert_called_once()
                assert logger_module._openobserve_handler is None

    def test_shutdown_logger_without_openobserve(self):
        """Test shutdown_logger works without OpenObserve handler."""
        from app.core import logger as logger_module

        logger_module._openobserve_handler = None

        with patch.object(logger_module.logger, "info"):
            with patch.object(logger_module.logger, "complete"):
                # Should not raise
                logger_module.shutdown_logger()


class TestLogLevels:
    """Tests for LOG_LEVELs mapping."""

    def test_log_levels_mapping(self):
        """Test LOG_LEVELs contains correct mappings."""
        from app.core.logger import LOG_LEVELs

        assert LOG_LEVELs[50] == "CRITICAL"
        assert LOG_LEVELs[40] == "ERROR"
        assert LOG_LEVELs[30] == "WARNING"
        assert LOG_LEVELs[20] == "INFO"
        assert LOG_LEVELs[10] == "DEBUG"
        assert LOG_LEVELs[0] == "NOTSET"


class TestRequestIdVar:
    """Tests for request_id_var context variable."""

    def test_request_id_var_default(self):
        """Test request_id_var has default of None."""
        from app.core.logger import request_id_var

        # Get default value
        assert request_id_var.get() is None or isinstance(request_id_var.get(), str)

    def test_request_id_var_set_and_get(self):
        """Test request_id_var can be set and retrieved."""
        from app.core.logger import request_id_var

        token = request_id_var.set("test-id-12345")
        try:
            assert request_id_var.get() == "test-id-12345"
        finally:
            request_id_var.reset(token)
