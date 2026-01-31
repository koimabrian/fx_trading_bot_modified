"""Logging Factory - Centralized logging configuration for entire application.

Provides consistent logging setup across all modules, eliminating boilerplate
logger initialization and ensuring uniform log formatting and levels.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional


class LoggingFactory:
    """Centralized logging configuration factory.

    Provides a single point to configure logging for the entire application.
    Eliminates duplicate logger setup code across modules.
    """

    _configured = False
    _loggers = {}
    _log_level = logging.INFO
    _log_dir = "logs"
    _log_file = "trading_bot.log"
    _max_bytes = 10_000_000  # 10 MB
    _backup_count = 5

    @staticmethod
    def configure(
        level: str = "INFO",
        log_dir: str = "logs",
        log_file: str = "trading_bot.log",
        max_bytes: int = 10_000_000,
        backup_count: int = 5,
    ) -> None:
        """Configure the logging system once at application startup.

        Should be called once before any logging occurs. Subsequent calls are ignored.

        Args:
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files (will be created if doesn't exist)
            log_file: Name of log file (without path)
            max_bytes: Max size of log file before rotation (default 10MB)
            backup_count: Number of backup log files to keep (default 5)

        Example:
            LoggingFactory.configure(
                level="INFO",
                log_dir="logs",
                log_file="trading_bot.log"
            )
            logger = LoggingFactory.get_logger(__name__)
        """
        if LoggingFactory._configured:
            return

        # Store configuration
        LoggingFactory._log_level = getattr(logging, level.upper(), logging.INFO)
        LoggingFactory._log_dir = log_dir
        LoggingFactory._log_file = log_file
        LoggingFactory._max_bytes = max_bytes
        LoggingFactory._backup_count = backup_count

        # Create log directory
        os.makedirs(log_dir, exist_ok=True)

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
        log_file_path = os.path.join(log_dir, log_file)
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

        Creates or returns a cached logger. Automatically configures logging
        if not already configured.

        Args:
            name: Logger name (typically __name__ of the calling module)

        Returns:
            Configured logger instance

        Example:
            logger = LoggingFactory.get_logger(__name__)
            logger.info("Application started")
        """
        # Auto-configure if not already done
        if not LoggingFactory._configured:
            LoggingFactory.configure()

        # Return cached logger if exists
        if name in LoggingFactory._loggers:
            return LoggingFactory._loggers[name]

        # Create new logger
        logger = logging.getLogger(name)
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
