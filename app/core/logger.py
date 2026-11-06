import logging
import os
import sys
import uuid
from contextvars import ContextVar
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from loguru import logger

from app.core.config import Environment, settings
from app.core.openobserve import add_openobserve_sink, is_openobserve_request_log, shutdown_openobserve

if TYPE_CHECKING:
    from types import FrameType

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
# CUSTOM FILTER FOR CORRELATION AND PROCESS ID
# ============================================


def correlation_filter(record: "Record") -> bool:
    """
    Add correlation ID and process ID to log records.
    This allows tracking requests across the application and
    differentiating between different worker processes.
    Drops the log shipper's own HTTP request logs, so shipping does not log itself.

    Args:
        record (Record): Log record from Loguru.

    Returns:
        bool: True to include the log, False to filter it out.
    """
    if record.get("name", None) and is_openobserve_request_log(record.get("message", "")):
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
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find the caller from where the logging call originated
        frame: Optional["FrameType"] = logging.currentframe()
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
    - Room for optional extra sinks (for example log shipping), all non-blocking

    This should be called once during application startup,
    preferably in the FastAPI lifespan startup event.
    """
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

    add_openobserve_sink(log_level, correlation_filter)

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
    logger.info("Shutting down logger...")

    shutdown_openobserve()

    # Let Loguru finish processing queued logs
    logger.complete()

    logger.info("Logger shutdown complete")
