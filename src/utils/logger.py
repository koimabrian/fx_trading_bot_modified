# fx_trading_bot/src/utils/logger.py
# Purpose: Configures logging for the application
import logging
import os
from datetime import datetime

# Global flag to prevent multiple logging initializations
_logging_configured = False

def setup_logging():
    """Configure logging for the application"""
    global _logging_configured
    if _logging_configured:
        return logging.getLogger(__name__)

    log_dir = 'logs'
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f'terminal_log.txt')
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Suppress matplotlib debug messages
    logging.getLogger('matplotlib').setLevel(logging.INFO)
    
    _logging_configured = True
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized. Log file: {log_file}")
    return logger