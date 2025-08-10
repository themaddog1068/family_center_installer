"""
Logging configuration for the application.
"""

import logging
import logging.config
import os
from pathlib import Path
from typing import Any


def get_logging_config() -> dict[str, Any]:
    """Get logging configuration dictionary.

    Returns:
        Dict containing logging configuration
    """
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s"
            },
            "json": {
                "format": '{"time": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
            },
        },
        "handlers": {
            "console": {
                "level": log_level,
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "level": log_level,
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "detailed",
                "filename": str(log_dir / "app.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
            "error_file": {
                "level": "ERROR",
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "detailed",
                "filename": str(log_dir / "error.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
        },
        "loggers": {
            "": {  # root logger
                "handlers": ["console", "file"],
                "level": log_level,
                "propagate": False,
            },
            "app": {
                "handlers": ["console", "file", "error_file"],
                "level": log_level,
                "propagate": False,
            },
        },
    }


def setup_logging() -> None:
    """Set up logging configuration."""
    logging.config.dictConfig(get_logging_config())


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
