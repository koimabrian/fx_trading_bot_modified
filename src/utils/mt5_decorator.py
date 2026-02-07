"""MT5 Connection Decorator - Automatic Retry Logic for MT5 Operations

This module provides decorators to add automatic reconnection and retry logic
to any MT5 method without cluttering the business logic.
"""

import time
from functools import wraps
from typing import Any, Callable

import MetaTrader5 as mt5

from src.utils.logging_factory import LoggingFactory

logger = LoggingFactory.get_logger(__name__)


def mt5_safe(max_retries: int = 5, retry_delay: float = 2.0, backoff: bool = True):
    """
    Decorator that adds automatic MT5 reconnection and retry logic to methods.

    This decorator:
    - Ensures MT5 is initialized before calling the method
    - Automatically retries on connection errors
    - Implements exponential backoff if enabled
    - Logs all retry attempts and failures

    Args:
        max_retries (int): Maximum number of retry attempts. Default: 5
        retry_delay (float): Initial delay between retries in seconds. Default: 2.0
        backoff (bool): Use exponential backoff (delay * 1.5 per retry). Default: True

    Returns:
        function: Decorated function with retry logic

    Example:
        @mt5_safe(max_retries=3, retry_delay=1.0)
        def place_order(self, symbol, volume, side, price=None):
            # Method implementation - no error handling needed
            ticket = mt5.order_send(request)
            return ticket
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs) -> Any:
            attempt = 0
            current_delay = retry_delay

            while attempt < max_retries:
                try:
                    # Ensure MT5 is initialized
                    if not mt5.initialize():
                        logger.warning(
                            "[MT5 RETRY %d/%d] MT5 not initialized, retrying %s...",
                            attempt + 1,
                            max_retries,
                            func.__name__,
                        )
                        attempt += 1
                        if attempt >= max_retries:
                            logger.error(
                                "[MT5 FAILED] %s failed after %d initialization attempts",
                                func.__name__,
                                max_retries,
                            )
                            return None
                        time.sleep(current_delay)
                        if backoff:
                            current_delay *= 1.5
                        continue

                    # Call the actual method
                    logger.debug("[MT5] Executing %s...", func.__name__)
                    result = func(self, *args, **kwargs)

                    # Reset counter and delay on success
                    attempt = 0
                    current_delay = retry_delay
                    return result

                except ConnectionError as e:
                    logger.warning(
                        "[MT5 CONNECTION ERROR] %s: %s", func.__name__, str(e)
                    )
                    attempt += 1
                    if attempt >= max_retries:
                        logger.error(
                            "[MT5 FAILED] %s failed after %d connection attempts",
                            func.__name__,
                            max_retries,
                        )
                        return None
                    logger.info(
                        "[MT5 RETRY] Attempt %d/%d, waiting %.1fs...",
                        attempt,
                        max_retries,
                        current_delay,
                    )
                    time.sleep(current_delay)
                    if backoff:
                        current_delay *= 1.5

                except TimeoutError as e:
                    logger.warning("[MT5 TIMEOUT] %s: %s", func.__name__, str(e))
                    attempt += 1
                    if attempt >= max_retries:
                        logger.error(
                            "[MT5 FAILED] %s timed out after %d attempts",
                            func.__name__,
                            max_retries,
                        )
                        return None
                    time.sleep(current_delay)
                    if backoff:
                        current_delay *= 1.5

                except ValueError as e:
                    # ValueError is typically a bad parameter, not a connection issue
                    logger.error("[MT5 VALIDATION ERROR] %s: %s", func.__name__, str(e))
                    return None

                except Exception as e:  # pylint: disable=broad-except
                    # Unexpected error - don't retry
                    logger.critical(
                        "[MT5 UNEXPECTED ERROR] %s: %s", func.__name__, str(e)
                    )
                    return None

            logger.error(
                "[MT5 EXHAUSTED] %s exhausted all %d retries",
                func.__name__,
                max_retries,
            )
            return None

        return wrapper

    return decorator


def mt5_log_call(log_level: str = "DEBUG"):
    """
    Simple decorator to log MT5 method calls and results.
    Useful for debugging without retry logic.

    Args:
        log_level (str): Logging level (DEBUG, INFO, WARNING). Default: DEBUG

    Example:
        @mt5_log_call(log_level="INFO")
        def check_balance(self):
            return mt5.account_info().balance
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs) -> Any:
            log_func = getattr(logger, log_level.lower(), logger.debug)

            log_func(
                "[MT5 CALL] %s with args: %s, kwargs: %s", func.__name__, args, kwargs
            )

            try:
                result = func(self, *args, **kwargs)
                log_func("[MT5 RESULT] %s returned: %s", func.__name__, result)
                return result
            except Exception as e:  # pylint: disable=broad-except
                logger.error("[MT5 ERROR] %s raised: %s", func.__name__, str(e))
                raise

        return wrapper

    return decorator
