import logging
import logging.handlers
import sys
from pathlib import Path
from typing import cast

from .environment import EnvironmentConfig


def setup_logging(config: EnvironmentConfig, log_file: Path | None = None) -> None:
    """
    Set up logging configuration based on the environment.

    Args:
        config: Environment configuration object
        log_file: Optional path to log file. If not provided, logs to stdout.
    """
    # Create logs directory if it doesn't exist
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

    # Configure logging format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Set up handlers
    handlers: list[logging.Handler] = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    handlers.append(console_handler)

    # File handler if log_file is provided
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"  # 10MB
        )
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        handlers.append(cast(logging.Handler, file_handler))

    # Configure root logger
    logging.basicConfig(level=config.log_level, handlers=handlers, force=True)

    # Set third-party loggers to WARNING level
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    # Log startup message
    logging.info(f"Logging initialized for {config.environment} environment")
