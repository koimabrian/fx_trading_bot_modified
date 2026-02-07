"""Error Handler - Centralized error handling for trading operations.

Provides consistent error handling, recovery strategies, and severity-based responses
across the entire trading system. Eliminates duplicate error handling patterns.
"""

from enum import Enum
from typing import Any, Callable, Optional

from src.utils.logging_factory import LoggingFactory


class ErrorSeverity(Enum):
    """Error severity levels for consistent handling and response."""

    RECOVERABLE = "recoverable"  # Retry automatically or fallback
    WARNING = "warning"  # Log but continue execution
    CRITICAL = "critical"  # Log and stop, may raise
    IGNORE = "ignore"  # Silent, no logging


class TradingError(Exception):
    """Base exception for trading-related errors with severity level."""

    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.WARNING):
        """Initialize trading error with message and severity.

        Args:
            message: Error description
            severity: ErrorSeverity level for this error
        """
        self.message = message
        self.severity = severity
        super().__init__(message)


class ErrorHandler:
    """Centralized error handler for trading bot operations.

    Maps error types to severity levels and provides consistent error handling
    across the entire application. Eliminates duplicate try/except patterns.
    """

    # Error type to (severity, description) mapping
    ERROR_MAP = {
        ValueError: (ErrorSeverity.WARNING, "Invalid parameters"),
        KeyError: (ErrorSeverity.CRITICAL, "Missing configuration"),
        ConnectionError: (ErrorSeverity.RECOVERABLE, "Connection issue"),
        TimeoutError: (ErrorSeverity.RECOVERABLE, "Operation timeout"),
        PermissionError: (ErrorSeverity.CRITICAL, "Account/permission restriction"),
        FileNotFoundError: (ErrorSeverity.CRITICAL, "Configuration file not found"),
        OSError: (ErrorSeverity.RECOVERABLE, "System I/O error"),
        RuntimeError: (ErrorSeverity.WARNING, "Runtime error"),
        AttributeError: (ErrorSeverity.WARNING, "Missing attribute"),
        TypeError: (ErrorSeverity.WARNING, "Type mismatch"),
    }

    @staticmethod
    def handle_error(
        error: Exception,
        context: str = "",
        retry_func: Optional[Callable] = None,
        error_count: Optional[int] = None,
        **kwargs,
    ) -> Any:
        """Handle an error with appropriate logging and recovery.

        Categorizes error by type, applies severity-based response, and optionally
        retries on recoverable errors.

        Args:
            error: The exception that occurred
            context: Where the error happened (e.g., "place_order", "fetch_data")
            retry_func: Optional function to call for automatic recovery
            error_count: Optional counter for tracking error frequency
            **kwargs: Additional context parameters (e.g., symbol) for logging

        Returns:
            None on failure, result of retry_func if retry successful, or None

        Examples:
            # Simple error handling
            try:
                result = risky_operation()
            except Exception as e:
                return ErrorHandler.handle_error(e, context="risky_operation")

            # With retry on recoverable errors
            try:
                result = fetch_data()
            except Exception as e:
                return ErrorHandler.handle_error(
                    e,
                    context="fetch_data",
                    retry_func=lambda: fetch_data()
                )
        """
        # Accept additional keyword arguments for context logging
        error_type = type(error)
        severity, default_msg = ErrorHandler.ERROR_MAP.get(
            error_type, (ErrorSeverity.WARNING, "Unknown error")
        )

        # Format error message
        error_msg = str(error) if str(error) else default_msg
        full_msg = f"{context}: {error_msg}" if context else error_msg

        logger = LoggingFactory.get_logger(__name__)

        if severity == ErrorSeverity.RECOVERABLE:
            logger.warning("[RECOVERABLE] %s", full_msg)
            if retry_func:
                logger.info("[RECOVERY] Attempting automatic recovery...")
                try:
                    result = retry_func()
                    logger.info("[RECOVERY] Recovery successful")
                    return result
                except Exception as retry_error:  # pylint: disable=broad-except
                    logger.warning("[RECOVERY FAILED] %s", str(retry_error))
            return None

        elif severity == ErrorSeverity.WARNING:
            logger.warning("[WARNING] %s", full_msg)
            return None

        elif severity == ErrorSeverity.CRITICAL:
            logger.critical("[CRITICAL] %s", full_msg)
            raise TradingError(full_msg, severity)

        elif severity == ErrorSeverity.IGNORE:
            # Silent failure - no logging
            return None

        return None

    @staticmethod
    def handle_validation_error(
        field: str, value: Any, expected_type: str = "", context: str = ""
    ) -> bool:
        """Handle validation errors for common cases.

        Args:
            field: Name of field that failed validation
            value: The invalid value
            expected_type: Expected type/format
            context: Where validation failed

        Returns:
            False (always fails validation)

        Examples:
            if not symbol or not isinstance(symbol, str):
                return ErrorHandler.handle_validation_error(
                    field="symbol",
                    value=symbol,
                    expected_type="str",
                    context="place_order"
                )
        """
        msg = f"Validation failed for {field}"
        if expected_type:
            msg += f" (expected {expected_type})"
        if context:
            msg += f" in {context}"
        msg += f": {value}"

        logger = LoggingFactory.get_logger(__name__)
        logger.warning("[VALIDATION] %s", msg)
        return False

    @staticmethod
    def log_error_summary(
        error_count: int = 0,
        warning_count: int = 0,
        critical_count: int = 0,
        operation: str = "",
    ) -> None:
        """Log a summary of errors encountered during an operation.

        Args:
            error_count: Number of recoverable errors
            warning_count: Number of warnings
            critical_count: Number of critical errors
            operation: Name of operation being summarized
        """
        logger = LoggingFactory.get_logger(__name__)
        
        if critical_count > 0:
            logger.critical(
                "[SUMMARY] %s: %d CRITICAL errors!",
                operation or "Operation",
                critical_count,
            )
        elif warning_count > 0:
            logger.warning(
                "[SUMMARY] %s: %d warnings, %d recoveries",
                operation or "Operation",
                warning_count,
                error_count,
            )
        elif error_count > 0:
            logger.info(
                "[SUMMARY] %s: %d recoverable errors handled",
                operation or "Operation",
                error_count,
            )
        else:
            logger.info(
                "[SUMMARY] %s: All operations successful", operation or "Operation"
            )

    @staticmethod
    def safe_get_config(config: dict, key: str, default: Any = None) -> Any:
        """Safely get a config value with error handling.

        Args:
            config: Config dictionary
            key: Dot-notation key (e.g., "risk_management.stop_loss_percent")
            default: Default value if key not found

        Returns:
            Config value or default if not found
        """
        try:
            keys = key.split(".")
            current = config
            for k in keys:
                current = current[k]
            return current
        except (KeyError, TypeError) as e:
            logger = LoggingFactory.get_logger(__name__)
            logger.warning("[CONFIG] Missing key '%s': %s", key, str(e))
            return default

    @staticmethod
    def should_retry(error: Exception) -> bool:
        """Determine if an error is recoverable and should be retried.

        Args:
            error: The exception to evaluate

        Returns:
            True if error is recoverable, False otherwise
        """
        error_type = type(error)
        severity, _ = ErrorHandler.ERROR_MAP.get(
            error_type, (ErrorSeverity.WARNING, "")
        )
        return severity == ErrorSeverity.RECOVERABLE
