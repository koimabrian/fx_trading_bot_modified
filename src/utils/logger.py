# fx_trading_bot/src/utils/logger.py
# Centralized logging setup

import logging
import os
import sys

def setup_logging():
    """Set up logging configuration for the application"""
    # Ensure logs directory exists
    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, 'terminal_log.txt')),
            logging.StreamHandler(sys.stdout)  # Output to console
        ]
    )