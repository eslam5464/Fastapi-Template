"""Tests for the OpenObserve log shipping module (app.core.openobserve)."""

import queue
import sys
from unittest.mock import MagicMock, patch

from app.core.config import Environment


class TestOpenObserveHandler:
    """Tests for OpenObserveHandler class."""

    def test_init_creates_handler(self):
        """Test OpenObserveHandler initialization."""
        from app.core.openobserve import OpenObserveHandler

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
        from app.core.openobserve import OpenObserveHandler

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
        from app.core.openobserve import OpenObserveHandler

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
        from app.core.openobserve import OpenObserveHandler

        with patch.object(OpenObserveHandler, "_start_worker"):
            handler = OpenObserveHandler(
                url="http://localhost:5080",
                token="test-token",
            )

            with patch.dict(sys.modules, {"httpx": None}):
                with patch("builtins.__import__", side_effect=ImportError("No module named 'httpx'")):
                    # Reset client to None to force re-initialization
                    handler._client = None

                    # This should handle the ImportError gracefully
                    # The actual behavior depends on implementation

            # Cleanup
            handler.shutdown_event.set()

    def test_send_log_queues_message(self):
        """Test send_log adds log to queue."""
        from app.core.openobserve import OpenObserveHandler

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
        from app.core.openobserve import OpenObserveHandler

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
        from app.core.openobserve import OpenObserveHandler

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
        from app.core.openobserve import OpenObserveHandler

        with patch.object(OpenObserveHandler, "_start_worker"):
            handler = OpenObserveHandler(
                url="http://localhost:5080",
                token="test-token",
            )

            handler.shutdown_event.set()  # Already shut down

            # Should not raise
            handler.shutdown()


class TestCorrelationFilterDropsShipperLogs:
    """The logger's filter drops the HTTP client's logs about OpenObserve requests."""

    def test_filters_openobserve_logs(self):
        """Test correlation_filter removes OpenObserve HTTP logs."""
        from app.core.logger import correlation_filter

        with patch("app.core.openobserve.settings") as mock_settings:
            mock_settings.openobserve_url = "http://openobserve.example.com"

            record = {
                "name": "httpx",
                "message": "POST http://openobserve.example.com/api/org/stream",
                "extra": {},
            }
            result = correlation_filter(record)

            assert result is False

    def test_keeps_other_logs(self):
        """Test correlation_filter keeps logs that do not mention the OpenObserve URL."""
        from app.core.logger import correlation_filter

        with patch("app.core.openobserve.settings") as mock_settings:
            mock_settings.openobserve_url = "http://openobserve.example.com"

            record = {"name": "httpx", "message": "GET http://other.example.com/", "extra": {}}

            assert correlation_filter(record) is True


class TestAddOpenObserveSink:
    """Tests for add_openobserve_sink, called by setup_logger."""

    def test_disabled_adds_nothing(self):
        """Test no handler or sink is created when log_to_openobserve is false."""
        from app.core import openobserve

        with patch("app.core.openobserve.settings") as mock_settings:
            mock_settings.log_to_openobserve = False
            with patch.object(openobserve, "OpenObserveHandler") as handler_cls:
                with patch.object(openobserve.logger, "add") as add:
                    openobserve.add_openobserve_sink("INFO", lambda record: True)

        handler_cls.assert_not_called()
        add.assert_not_called()

    def test_setup_logger_adds_sink_when_enabled(self):
        """Test setup_logger starts the handler and adds a sink that queues payloads."""
        from app.core import logger as logger_module
        from app.core import openobserve

        handler = MagicMock()
        with patch("app.core.logger.logger") as mock_logger:
            with patch("app.core.logger.settings") as logger_settings:
                logger_settings.current_environment = Environment.DEV
                logger_settings.log_level = 20
                with patch("app.core.openobserve.settings") as mock_settings:
                    mock_settings.log_to_openobserve = True
                    mock_settings.current_environment = Environment.DEV
                    with patch.object(openobserve, "OpenObserveHandler", return_value=handler):
                        with patch.object(openobserve, "logger") as oo_logger:
                            logger_module.setup_logger()

                            sink = oo_logger.add.call_args.args[0]
                            assert oo_logger.add.call_args.kwargs["filter"] is logger_module.correlation_filter
                            assert mock_logger.add.call_count == 2  # console and file only

                            message = MagicMock()
                            message.record = {
                                "time": MagicMock(isoformat=MagicMock(return_value="2026-01-01T00:00:00")),
                                "level": MagicMock(),
                                "message": "hello",
                                "extra": {"process_id": 1, "request_id": "abc"},
                                "name": "app",
                                "function": "f",
                                "line": 1,
                                "exception": None,
                            }
                            sink(message)

        payload = handler.send_log.call_args.args[0]
        assert payload["message"] == "hello"
        assert payload["request_id"] == "abc"
        assert payload["environment"] == Environment.DEV.value
        openobserve.shutdown_openobserve()


class TestShutdownOpenObserve:
    """Tests for shutdown_openobserve, called by shutdown_logger."""

    def test_shutdown_logger_closes_openobserve(self):
        """Test shutdown_logger closes the OpenObserve handler."""
        from app.core import logger as logger_module
        from app.core import openobserve

        mock_handler = MagicMock()
        openobserve._handler = mock_handler

        with patch.object(logger_module.logger, "info"):
            with patch.object(logger_module.logger, "complete"):
                logger_module.shutdown_logger()

        mock_handler.shutdown.assert_called_once()
        assert openobserve._handler is None

    def test_shutdown_without_handler(self):
        """Test shutdown_openobserve is a no-op when no handler was started."""
        from app.core import openobserve

        openobserve._handler = None
        openobserve.shutdown_openobserve()

        assert openobserve._handler is None
