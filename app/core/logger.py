import asyncio
import logging
import os
import sys
from typing import Any

import aiohttp
from loguru import logger

from app.core.config import settings


def safe_serialize(obj):
    """Safely serialize objects to JSON-compatible types"""
    if obj is None:
        return None
    elif isinstance(obj, (str, int, float, bool)):
        return obj
    elif isinstance(obj, (list, tuple)):
        return [safe_serialize(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: safe_serialize(value) for key, value in obj.items()}
    else:
        # For any other type, convert to string
        return str(obj)


class AsyncOpenObserveSink:
    def __init__(
        self,
        url: str,
        org_id: str,
        stream_name: str,
        access_key: str,
        batch_size: int = 10,
        flush_interval: int = 5,
    ):
        self.url = f"{url.rstrip('/')}/api/{org_id}/{stream_name}/_json"
        self.headers = {"Content-Type": "application/json", "Authorization": f"Basic {access_key}"}
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.log_queue = asyncio.Queue()
        self.session = None
        self._task = None
        self._shutdown_event = asyncio.Event()

    async def start(self):
        """Start the async sink"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            connector=aiohttp.TCPConnector(limit=100, limit_per_host=30),
        )
        self._task = asyncio.create_task(self._worker())

    async def stop(self):
        """Stop the async sink and cleanup resources"""
        self._shutdown_event.set()
        if self._task:
            await self._task
        if self.session:
            await self.session.close()

    async def _worker(self):
        """Background worker to process logs in batches"""
        while not self._shutdown_event.is_set():
            try:
                logs_to_send = []

                # Try to collect logs for batch processing
                try:
                    # Wait for at least one log or timeout
                    first_log = await asyncio.wait_for(
                        self.log_queue.get(), timeout=self.flush_interval
                    )
                    logs_to_send.append(first_log)

                    # Get additional logs up to batch_size
                    for _ in range(self.batch_size - 1):
                        try:
                            log = await asyncio.wait_for(self.log_queue.get(), timeout=0.1)
                            logs_to_send.append(log)
                        except asyncio.TimeoutError:
                            break

                except asyncio.TimeoutError:
                    # No logs received within timeout, continue loop
                    continue

                # Send logs if we have any
                if logs_to_send:
                    await self._send_logs(logs_to_send)

            except Exception as e:
                print(f"Error in AsyncOpenObserve worker: {e}")

    async def _send_logs(self, logs: list[dict[str, Any]]):
        """Send logs to OpenObserve asynchronously"""
        if not self.session:
            print("Session not initialized")
            return

        try:
            async with self.session.post(self.url, headers=self.headers, json=logs) as response:
                if response.status != 200:
                    text = await response.text()
                    print(
                        f"Failed to send logs to OpenObserve. "
                        f"Status: {response.status}, Response: {text}"
                    )
        except aiohttp.ClientError as e:
            print(f"Error sending logs to OpenObserve: {e}")
        except Exception as e:
            print(f"Unexpected error sending logs: {e}")

    def __call__(self, message):
        """Loguru sink function - puts log into async queue"""
        record = message.record

        # Extract file information more thoroughly
        file_info = record.get("file")
        if file_info and hasattr(file_info, "name"):
            file_name = file_info.name
            file_path = str(file_info.path) if hasattr(file_info, "path") else file_name
        else:
            file_name = str(file_info) if file_info else ""
            file_path = file_name

        # Extract process information
        process_info = record.get("process")
        if process_info and hasattr(process_info, "name"):
            process_name = process_info.name
            process_id = getattr(process_info, "id", 0)
        else:
            process_name = str(process_info) if process_info else "MainProcess"
            process_id = 0

        # Extract thread information
        thread_info = record.get("thread")
        if thread_info and hasattr(thread_info, "name"):
            thread_name = thread_info.name
            thread_id = getattr(thread_info, "id", 0)
        else:
            thread_name = str(thread_info) if thread_info else "MainThread"
            thread_id = 0

        # Extract log data with enhanced fields
        log_entry = {
            "@timestamp": safe_serialize(record["time"].isoformat()),
            "level": safe_serialize(record["level"].name),
            "message": safe_serialize(record["message"]),
            "logger": safe_serialize(record["name"]),
            "module": safe_serialize(record["name"]),
            "function": safe_serialize(record["function"]),
            "line": safe_serialize(record["line"]),
            "file": os.path.basename(file_name) if file_name else "",
            "file_path": safe_serialize(file_path),
            "process": safe_serialize(process_name),
            "process_id": safe_serialize(process_id),
            "thread": safe_serialize(thread_name),
            "thread_id": safe_serialize(thread_id),
        }

        # Add exception info if present
        if record["exception"]:
            log_entry["exception"] = {
                "type": record["exception"].type.__name__ if record["exception"].type else None,
                "value": str(record["exception"].value) if record["exception"].value else None,
                "traceback": (
                    str(record["exception"].traceback) if record["exception"].traceback else None
                ),
            }

        # Add extra fields
        if record["extra"]:
            for key, value in record["extra"].items():
                log_entry[f"extra_{key}"] = safe_serialize(value)

        # Add to queue for batch processing (non-blocking)
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, schedule the put
                asyncio.create_task(self.log_queue.put(log_entry))
            else:
                # If no event loop is running, use the synchronous approach
                # This handles cases where logging happens outside async context
                loop.run_until_complete(self.log_queue.put(log_entry))
        except RuntimeError:
            # Fallback: if no event loop exists, we'll need to handle this differently
            # You might want to use a thread-safe queue as fallback
            print(f"Warning: Could not add log to async queue: {log_entry['message']}")


class InterceptHandler(logging.Handler):
    """
    Intercept standard logging messages toward loguru sinks.
    """

    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2

        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


# Global reference to the async sink for cleanup
_async_sink = None


async def configure_async_logging() -> None:
    """
    Configure the async logging system for the application
    """
    global _async_sink

    # Remove default logger
    logger.remove()

    if settings.log_to_openobserve is True:
        _async_sink = AsyncOpenObserveSink(
            url=settings.openobserve_url,
            org_id=settings.openobserve_org_id,
            stream_name=settings.openobserve_stream_name,
            access_key=settings.openobserve_access_key,
            batch_size=10,  # Send logs in batches of 10
            flush_interval=5,  # Send every 5 seconds
        )

        # Start the async sink
        await _async_sink.start()

    # Log format for console output
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss!UTC}</green> | "
        "<magenta>{process: <6}</magenta> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    log_file_format = (
        "{time:YYYY-MM-DD HH:mm:ss!UTC} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )

    # Add console handler
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.log_level,
        colorize=True,
    )

    # Add a file handler for more detailed logs
    logger.add(
        f"logs{os.sep}app.log",
        rotation="10 MB",
        retention="1 month",
        compression="zip",
        format=log_file_format,
        level=logging.NOTSET,
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Set up loggers for FastAPI, Uvicorn, and other libraries
    loggers_to_intercept = [
        "fastapi",
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "sqlalchemy.engine",
        "sqlalchemy.pool",
        "httpx",
        "redis",
    ]

    for logger_name in loggers_to_intercept:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False

    if settings.log_to_openobserve is True and _async_sink:
        logger.add(
            sink=_async_sink,
            level=logging.INFO,
            backtrace=True,
            diagnose=True,
        )

    # Log the start of the application
    logger.info(f"Async logging configured with level {settings.log_level}")


async def cleanup_logging():
    """Cleanup async logging resources"""
    global _async_sink
    if _async_sink:
        await _async_sink.stop()


# Main async logging configuration function
async def configure_logging() -> None:
    """
    Configure the async logging system for the application
    """
    await configure_async_logging()
