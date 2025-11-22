import atexit
import logging
import os
import queue
import sys
import threading
import time
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from loguru import logger

from app.core.config import Environment, settings

if TYPE_CHECKING:
    from loguru import Record

# ============================================
# CONTEXT VARIABLES FOR REQUEST TRACKING
# ============================================
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


# ============================================
# LOG DIRECTORY AND FILE PATHS
# ============================================
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Single unified log file for all workers
LOG_FILE = LOG_DIR / "app.log"


# ============================================
# LOG LEVEL MAPPING
# ============================================

LOG_LEVELs = {
    50: "CRITICAL",
    40: "ERROR",
    30: "WARNING",
    20: "INFO",
    10: "DEBUG",
    0: "NOTSET",
}


# ============================================
# OPENOBSERVE ASYNC HANDLER
# ============================================


class OpenObserveHandler:
    """
    Thread-safe, non-blocking handler for sending logs to OpenObserve.

    Features:
    - Background thread for HTTP requests (doesn't block FastAPI event loop)
    - Batching for efficiency (reduces HTTP calls)
    - Queue-based to avoid blocking main application
    - Automatic retry with exponential backoff
    - Graceful shutdown with pending log flush
    - Connection pooling for performance
    """

    def __init__(
        self,
        url: str,
        token: str,
        org: str = "default",
        stream: str = "default",
        batch_size: int = 10,
        flush_interval: float = 5.0,
        max_retries: int = 3,
    ):
        self.url = url
        self.token = token
        self.org = org
        self.stream = stream
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_retries = max_retries

        # Queue for log messages (thread-safe)
        self.log_queue: queue.Queue = queue.Queue(maxsize=1000)

        # Background thread
        self.worker_thread: Optional[threading.Thread] = None
        self.shutdown_event = threading.Event()

        # HTTP client (lazy initialization)
        self._client = None
        self._client_lock = threading.Lock()

        # Start background worker
        self._start_worker()

        # Register shutdown handler
        atexit.register(self.shutdown)

    def _get_client(self):
        """Lazy initialization of HTTP client with connection pooling"""
        if self._client is None:
            with self._client_lock:
                if self._client is None:  # Double-check locking
                    try:
                        import httpx

                        self._client = httpx.Client(
                            timeout=10.0,
                            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                        )
                    except ImportError:
                        print(
                            "WARNING: httpx not installed. OpenObserve logging disabled.",
                            file=sys.stderr,
                        )
                        print("Install with: pip install httpx", file=sys.stderr)
                        return None
        return self._client

    def _start_worker(self):
        """Start background thread for processing logs"""
        self.worker_thread = threading.Thread(
            target=self._worker_loop, daemon=True, name="OpenObserveWorker"
        )
        self.worker_thread.start()

    def _worker_loop(self):
        """Background worker that batches and sends logs"""
        batch: list[dict[str, Any]] = []
        last_flush = time.time()

        while not self.shutdown_event.is_set():
            try:
                # Try to get a log with timeout
                try:
                    log_entry = self.log_queue.get(timeout=1.0)
                    batch.append(log_entry)
                except queue.Empty:
                    pass

                # Flush if batch is full or time interval elapsed
                current_time = time.time()
                should_flush = len(batch) >= self.batch_size or (
                    batch and (current_time - last_flush) >= self.flush_interval
                )

                if should_flush:
                    self._flush_batch(batch)
                    batch.clear()
                    last_flush = current_time

            except Exception as e:
                print(f"OpenObserve worker error: {e}", file=sys.stderr)

        # Flush remaining logs on shutdown
        if batch:
            self._flush_batch(batch)

    def _flush_batch(self, batch: list[dict[str, Any]]):
        """Send batch of logs to OpenObserve with retry logic"""
        if not batch:
            return

        client = self._get_client()
        if client is None:
            return

        endpoint = f"{self.url}/api/{self.org}/{self.stream}/_json"
        headers = {"Authorization": f"Basic {self.token}", "Content-Type": "application/json"}

        for attempt in range(self.max_retries):
            try:
                response = client.post(endpoint, json=batch, headers=headers)
                response.raise_for_status()
                return  # Success

            except Exception as e:
                if attempt == self.max_retries - 1:
                    print(
                        f"Failed to send {len(batch)} logs to OpenObserve after {self.max_retries} attempts: {e}",
                        file=sys.stderr,
                    )
                else:
                    # Exponential backoff
                    time.sleep(2**attempt)

    def send_log(self, log_data: dict[str, Any]):
        """
        Add log to queue for async sending.
        Non-blocking call - returns immediately.
        """
        try:
            self.log_queue.put_nowait(log_data)
        except queue.Full:
            print("OpenObserve queue full, dropping log", file=sys.stderr)

    def shutdown(self):
        """Gracefully shutdown the handler and flush pending logs"""
        if self.shutdown_event.is_set():
            return

        print("Shutting down OpenObserve handler...", file=sys.stderr)
        self.shutdown_event.set()

        # Wait for worker to finish (max 10 seconds)
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=10.0)

        # Close HTTP client
        if self._client:
            self._client.close()

        print("OpenObserve handler shutdown complete", file=sys.stderr)


# Global OpenObserve handler instance
_openobserve_handler: Optional[OpenObserveHandler] = None


# ============================================
# CUSTOM FILTER FOR CORRELATION AND PROCESS ID
# ============================================


def correlation_filter(record: "Record") -> bool:
    """
    Add correlation ID and process ID to log records.
    This allows tracking requests across the application and
    differentiating between different worker processes.
    Removes OpenObserve HTTP logs to avoid redundancy.

    Args:
        record (Record): Log record from Loguru.

    Returns:
        bool: True to include the log, False to filter it out.
    """
    if record.get("name", None):
        message = record.get("message", "")

        if settings.openobserve_url in message:
            return False

    record["extra"]["request_id"] = request_id_var.get() or str(uuid.uuid4())[:8]
    record["extra"]["process_id"] = os.getpid()

    return True


# ============================================
# INTERCEPT HANDLER FOR STANDARD LOGGING
# ============================================


class InterceptHandler(logging.Handler):
    """
    Intercepts standard logging and redirects to Loguru.
    Used to replace Uvicorn's default loggers with our Loguru configuration.
    """

    def emit(self, record: logging.LogRecord):
        """
        Process a log record and redirect it to Loguru.

        This method is called by the logging framework for each log record.
        We extract the log level and message, then pass it to Loguru.
        """
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find the caller from where the logging call originated
        frame = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        # Log to Loguru with the appropriate level and context
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


# ============================================
# MAIN LOGGER SETUP FUNCTION
# ============================================


def setup_logger():
    """
    Configure Loguru logger for multi-worker FastAPI application.

    Features:
    - Thread and process safe with enqueue=True
    - Single unified log file with process IDs for worker differentiation
    - 3 months retention, 10MB rotation
    - Compression for old logs (gzip)
    - Different outputs for console vs file
    - OpenObserve integration (optional, non-blocking)

    This should be called once during application startup,
    preferably in the FastAPI lifespan startup event.
    """
    global _openobserve_handler

    # Remove default handler to avoid duplicate logs
    logger.remove()

    # Get log level based on environment
    log_level = LOG_LEVELs[settings.log_level]

    # ============================================
    # CONSOLE OUTPUT: Simplified, colored format
    # ============================================
    # Purpose: Quick debugging and monitoring
    # Format: Timestamp | Level | PID | RequestID | Message
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<magenta>PID:{extra[process_id]}</magenta> | "
        "<yellow>ReqID:{extra[request_id]}</yellow> | "
        "<cyan>{name}:{function}:{line}</cyan> | "
        "<level>{message}</level>"
    )

    logger.add(
        sys.stdout,
        format=console_format,
        level=logging.DEBUG if settings.current_environment == Environment.DEV else logging.INFO,
        colorize=True,
        enqueue=True,  # Thread-safe queue-based logging
        filter=correlation_filter,
    )

    # ============================================
    # FILE OUTPUT: Detailed format with full context
    # ============================================
    # Purpose: Detailed logging for analysis and debugging
    # Format: Timestamp | Level | PID | RequestID | Module:Function:Line | Message
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss!UTC} | "
        "{level: <8} | "
        "PID:{extra[process_id]} | "
        "ReqID:{extra[request_id]} | "
        "{name}:{function}:{line} | "
        "{message}"
    )

    logger.add(
        LOG_FILE,
        format=file_format,
        level=log_level,
        rotation="10 MB",  # Rotate when file reaches 10MB
        retention="3 months",  # Keep logs for 3 months
        compression="gz",  # Compress rotated files to .gz
        enqueue=True,  # Process-safe queue for multi-worker safety
        serialize=False,  # Plain text format (.log file)
        filter=correlation_filter,
        backtrace=True,  # Enable full traceback on exceptions
        diagnose=True,  # Show variable values in exceptions
    )

    # ============================================
    # OPENOBSERVE SINK (Optional, Non-Blocking)
    # ============================================

    if settings.log_to_openobserve is True:
        # Initialize OpenObserve handler
        _openobserve_handler = OpenObserveHandler(
            url=settings.openobserve_url,
            token=settings.openobserve_access_key,
            org=settings.openobserve_org_id,
            stream=settings.openobserve_stream_name,
            batch_size=settings.openobserve_batch_size,
            flush_interval=settings.openobserve_flush_interval,
        )

        def openobserve_sink(message):
            """
            Non-blocking sink that queues logs for OpenObserve.
            This function is called by Loguru for each log entry.
            It immediately queues the log and returns, avoiding any blocking I/O.
            """
            if _openobserve_handler is None:
                return

            record: dict = message.record

            # Prepare payload for OpenObserve
            payload = {
                "timestamp": record["time"].isoformat(),
                "level": record["level"].name,
                "message": record["message"],
                "process_id": record["extra"].get("process_id"),
                "request_id": record["extra"].get("request_id"),
                "module": record["name"],
                "function": record["function"],
                "line": record["line"],
                "environment": settings.current_environment.value,
            }

            # Add exception info if present
            if record["exception"]:
                payload["exception"] = str(record["exception"])

            # Non-blocking: just queue the log
            _openobserve_handler.send_log(payload)

        logger.add(
            openobserve_sink,
            level=log_level,
            enqueue=True,  # Additional thread safety
            filter=correlation_filter,
        )

        logger.info(
            f"OpenObserve logging enabled (non-blocking) | "
            f"URL: {settings.openobserve_url} | "
            f"Batch: {settings.openobserve_batch_size} | "
            f"Flush: {settings.openobserve_flush_interval}s"
        )

    logger.info(
        f"Logger initialized | "
        f"Environment: {settings.current_environment.value} | "
        f"Level: {log_level} | "
        f"Workers: Multi-process safe"
    )


# ============================================
# UVICORN LOGGER CONFIGURATION
# ============================================


def configure_uvicorn_logging():
    """
    Replace Uvicorn's default logging with Loguru.

    This intercepts all standard library logging calls from Uvicorn
    and redirects them through our Loguru configuration, ensuring
    consistent log formatting across the entire application.

    Call this during FastAPI app startup, after setup_logger().
    """
    import logging

    # Intercept all loggers and set to lowest level
    # Loguru will handle the actual filtering
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Update existing loggers, especially Uvicorn loggers
    for name in logging.root.manager.loggerDict.keys():
        if name.startswith("uvicorn"):
            logging.getLogger(name).handlers = [InterceptHandler()]
            logging.getLogger(name).propagate = False

    logger.debug("Uvicorn logging configured to use Loguru")


# ============================================
# SHUTDOWN HANDLER
# ============================================


def shutdown_logger():
    """
    Gracefully shutdown logger and flush all pending logs.
    Call this in FastAPI shutdown event.
    """
    global _openobserve_handler

    logger.info("Shutting down logger...")

    # Shutdown OpenObserve handler
    if _openobserve_handler:
        _openobserve_handler.shutdown()
        _openobserve_handler = None

    # Let Loguru finish processing queued logs
    logger.complete()

    logger.info("Logger shutdown complete")
