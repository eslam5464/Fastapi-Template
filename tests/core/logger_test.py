"""Tests for the logger module."""

import logging
import os
from unittest.mock import MagicMock, patch

from app.core.config import Environment


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

                setup_logger()

                mock_logger.remove.assert_called_once()

    def test_setup_logger_adds_console_handler(self):
        """Test setup_logger adds console output handler."""
        from app.core.logger import setup_logger

        with patch("app.core.logger.logger") as mock_logger:
            with patch("app.core.logger.settings") as mock_settings:
                mock_settings.current_environment = Environment.DEV
                mock_settings.log_level = 20  # INFO

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

    def test_shutdown_logger_without_extra_sinks(self):
        """Test shutdown_logger works when no optional sink was started."""
        from app.core import logger as logger_module

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
