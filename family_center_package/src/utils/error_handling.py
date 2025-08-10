"""Error handling utilities."""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from src.core.display import Display, DisplayType
from src.utils.errors import ErrorSeverity, FamilyCenterError


def handle_error(severity: ErrorSeverity = ErrorSeverity.ERROR) -> Callable:
    """Decorator for handling errors in functions.

    Args:
        severity: Error severity level

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_error(
                    f"Error in {func.__name__}: {str(e)}",
                    severity=severity,
                    error=e,
                )
                raise_error(
                    f"Error in {func.__name__}: {str(e)}",
                    severity=severity,
                    error=e,
                )
                return None

        return wrapper

    return decorator


def log_error(
    message: str,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    error: Exception | None = None,
) -> None:
    """Log an error message.

    Args:
        message: Error message
        severity: Error severity
        error: Optional exception
    """
    logger = logging.getLogger(__name__)
    log_func = getattr(logger, severity.value)
    log_func(message, exc_info=error)


def raise_error(
    message: str,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    error: Exception | None = None,
) -> None:
    """Raise an error.

    Args:
        message: Error message
        severity: Error severity
        error: Optional exception

    Raises:
        FamilyCenterError: If error is not None
        Exception: If error is None
    """
    if error is not None:
        # If the error is already a FamilyCenterError, preserve it
        if isinstance(error, FamilyCenterError):
            raise error
        raise FamilyCenterError(message, severity) from error
    raise FamilyCenterError(message, severity)


def display_warning(message: str) -> None:
    """Display a warning message.

    Args:
        message: Warning message
    """
    display = Display(
        id="error-handler",
        name="Error Handler",
        type=DisplayType.DIGITAL,
        location="System",
    )
    display.set_error(message)


def display_error(message: str) -> None:
    """Display an error message.

    Args:
        message: Error message
    """
    display = Display(
        id="error-handler",
        name="Error Handler",
        type=DisplayType.DIGITAL,
        location="System",
    )
    display.set_error(message)
