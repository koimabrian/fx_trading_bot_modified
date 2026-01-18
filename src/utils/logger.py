"""Centralized logging configuration for the FX Trading Bot.

Sets up file and console handlers with appropriate log levels
and formatting for development and production environments.
"""

import logging
import os

# Global flag to prevent multiple logging initializations
LOGGING_CONFIGURED = False


def setup_logging():
    """Configure logging for the application"""
    global LOGGING_CONFIGURED  # pylint: disable=global-statement
    if LOGGING_CONFIGURED:
        return logging.getLogger(__name__)

    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, "terminal_log.txt")

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

    # Suppress matplotlib debug messages
    logging.getLogger("matplotlib").setLevel(logging.INFO)

    LOGGING_CONFIGURED = True
    logger = logging.getLogger(__name__)
    logger.info("Logging initialized. Log file: %s", log_file)
    return logger
