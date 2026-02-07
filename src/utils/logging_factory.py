"""Logging Factory - Centralized logging configuration for entire application.

Provides consistent logging setup across all modules, eliminating boilerplate
logger initialization and ensuring uniform log formatting and levels.
"""

import logging
import os
from logging.handlers import RotatingFileHandler


class LoggingFactory:
    """Centralized logging configuration factory.

    Provides a single point to configure logging for the entire application.
    Eliminates duplicate logger setup code across modules.
    """

    _configured = False
    _loggers = {}
    _log_level = logging.INFO
    _log_dir = "logs"
    _max_bytes = 10_000_000  # 10 MB
    _backup_count = 5
    _current_mode = None

    @staticmethod
    def configure(
        level: str = "INFO",
        log_dir: str = "logs",
        log_file: str = None,
        mode: str = None,
        max_bytes: int = 10_000_000,
        backup_count: int = 5,
        clear_on_start: bool = True,
    ) -> None:
        """Configure the logging system once at application startup.

        Should be called once before any logging occurs. Subsequent calls are ignored.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files (will be created if doesn't exist)
            log_file: Name of log file (without path). If None, uses mode-based name.
            mode: Operating mode (init, sync, backtest, live, gui, test)
            max_bytes: Max size of log file before rotation (default 10MB)
            backup_count: Number of backup log files to keep (default 5)
            clear_on_start: If True, clears the log file at startup (default True)

        Example:
            LoggingFactory.configure(
                level="INFO",
                log_dir="logs",
                mode="backtest"
            )
            logger = LoggingFactory.get_logger(__name__)
        """
        if LoggingFactory._configured:
            return

        # Determine log file name based on mode
        if log_file is None:
            if mode:
                log_file = f"{mode}_run.log"
            else:
                log_file = "trading_bot.log"

        # Store configuration
        LoggingFactory._log_level = getattr(logging, level.upper(), logging.INFO)
        LoggingFactory._log_dir = log_dir
        LoggingFactory._log_file = log_file
        LoggingFactory._max_bytes = max_bytes
        LoggingFactory._backup_count = backup_count
        LoggingFactory._current_mode = mode

        # Create log directory
        os.makedirs(log_dir, exist_ok=True)

        # Clear log file if requested (fresh logs for each run)
        log_file_path = os.path.join(log_dir, log_file)
        if clear_on_start and os.path.exists(log_file_path):
            try:
                open(log_file_path, "w").close()  # Truncate file
            except (OSError, IOError):
                pass  # Ignore errors if file is locked

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(LoggingFactory._log_level)

        # Remove existing handlers to avoid duplicates
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Create formatters
        console_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(LoggingFactory._log_level)
        console_handler.setFormatter(console_format)
        root_logger.addHandler(console_handler)

        # File handler with rotation
        try:
            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
            )
            file_handler.setLevel(LoggingFactory._log_level)
            file_handler.setFormatter(file_format)
            root_logger.addHandler(file_handler)
        except (OSError, IOError) as e:
            root_logger.error("Failed to setup file handler: %s", e)

        LoggingFactory._configured = True

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a logger instance with the given name.

        Creates or returns a cached logger. Does NOT auto-configure logging -
        relies on explicit configure() call from main.py before first log output.

        Args:
            name: Logger name (typically __name__ of the calling module)

        Returns:
            Configured logger instance

        Example:
            logger = LoggingFactory.get_logger(__name__)
            logger.info("Application started")
        """
        # Return cached logger if exists
        if name in LoggingFactory._loggers:
            return LoggingFactory._loggers[name]

        # Create new logger (will inherit from root logger once configured)
        logger = logging.getLogger(name)

        # Only set level if already configured
        if LoggingFactory._configured:
            logger.setLevel(LoggingFactory._log_level)

        # Cache it
        LoggingFactory._loggers[name] = logger

        return logger

    @staticmethod
    def set_level(level: str) -> None:
        """Change logging level for all loggers.

        Args:
            level: New logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

        Example:
            LoggingFactory.set_level("DEBUG")  # Enable debug logging
        """
        log_level = getattr(logging, level.upper(), logging.INFO)
        LoggingFactory._log_level = log_level

        # Update root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        # Update all handlers
        for handler in root_logger.handlers:
            handler.setLevel(log_level)

        # Update cached loggers
        for logger in LoggingFactory._loggers.values():
            logger.setLevel(log_level)

    @staticmethod
    def get_configured() -> bool:
        """Check if logging has been configured.

        Returns:
            True if configure() has been called, False otherwise
        """
        return LoggingFactory._configured

    @staticmethod
    def reset() -> None:
        """Reset logging factory to unconfigured state.

        Useful for testing. Clears all cached loggers and resets configuration.
        """
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        LoggingFactory._configured = False
        LoggingFactory._loggers.clear()
