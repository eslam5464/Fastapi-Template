"""Optional log shipping to OpenObserve (non-blocking, batched, over HTTP).

`app.core.logger` calls `add_openobserve_sink()` from `setup_logger()` and
`shutdown_openobserve()` from `shutdown_logger()`. Nothing here runs unless
`settings.log_to_openobserve` is true.
"""

import atexit
import queue
import sys
import threading
import time
from typing import TYPE_CHECKING, Any, Callable, Optional

from loguru import logger

from app.core.config import settings

if TYPE_CHECKING:
    import httpx
    from loguru import Record


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
        self._client: Optional["httpx.Client"] = None
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
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="OpenObserveWorker")
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


# Global OpenObserve handler instance (set by add_openobserve_sink)
_handler: Optional[OpenObserveHandler] = None


def is_openobserve_request_log(message: str) -> bool:
    """True for the HTTP client's own log lines about requests to OpenObserve.

    The logger's filter drops these, so shipping a batch does not log a line
    that is then shipped again.
    """
    return settings.openobserve_url in message


def add_openobserve_sink(log_level: str, log_filter: Callable[["Record"], bool]) -> None:
    """Start the OpenObserve handler and add its loguru sink, when enabled in settings.

    Args:
        log_level: Minimum level of the records sent to OpenObserve.
        log_filter: The logger's record filter (adds the request and process IDs).
    """
    global _handler

    if settings.log_to_openobserve is not True:
        return

    _handler = OpenObserveHandler(
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
        if _handler is None:
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
        _handler.send_log(payload)

    logger.add(
        openobserve_sink,
        level=log_level,
        enqueue=True,  # Additional thread safety
        filter=log_filter,
    )

    logger.info(
        f"OpenObserve logging enabled (non-blocking) | "
        f"URL: {settings.openobserve_url} | "
        f"Batch: {settings.openobserve_batch_size} | "
        f"Flush: {settings.openobserve_flush_interval}s"
    )


def shutdown_openobserve() -> None:
    """Flush pending logs and stop the OpenObserve handler, if it was started."""
    global _handler

    if _handler:
        _handler.shutdown()
        _handler = None
