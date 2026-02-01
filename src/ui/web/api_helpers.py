"""API helper utilities for Flask routes.

Provides common patterns for error handling, response formatting, and data validation
to reduce code duplication across dashboard API endpoints.
"""

from typing import Any, Dict, Tuple

from flask import jsonify

from src.utils.logging_factory import LoggingFactory


def safe_api_call(
    func, default_data: Any = None, error_message_prefix: str = "Operation failed"
) -> Tuple[Dict, int]:
    """Execute an API call with standardized error handling.

    Args:
        func: Callable that performs the API operation
        default_data: Default value to return on error (empty list, dict, etc.)
        error_message_prefix: Prefix for error log messages

    Returns:
        Tuple of (jsonify response, HTTP status code)

    Example:
        >>> response, status = safe_api_call(
        ...     lambda: fetch_data(),
        ...     default_data=[],
        ...     error_message_prefix="Failed to fetch results"
        ... )
    """
    logger = LoggingFactory.get_logger(__name__)

    if default_data is None:
        default_data = {}

    try:
        result = func()
        return jsonify({"data": result, "status": "success"}), 200

    except (RuntimeError, ValueError, KeyError) as e:
        logger.error("%s: %s", error_message_prefix, e)
        error_response = {"data": default_data, "status": "error", "message": str(e)}
        return jsonify(error_response), 500

    except Exception as e:
        logger.error("%s (Unexpected): %s", error_message_prefix, e)
        error_response = {
            "data": default_data,
            "status": "error",
            "message": "Unexpected error occurred",
        }
        return jsonify(error_response), 500


def api_response(
    data: Any, status: str = "success", message: str = None, status_code: int = 200
) -> Tuple[Dict, int]:
    """Format a standardized API response.

    Args:
        data: Response data (list, dict, or scalar)
        status: Status string ('success' or 'error')
        message: Optional error message
        status_code: HTTP status code

    Returns:
        Tuple of (jsonify response, HTTP status code)

    Example:
        >>> response, code = api_response(
        ...     {"symbols": ["EURUSD", "GBPUSD"]},
        ...     status="success"
        ... )
    """
    response_dict = {"data": data, "status": status}

    if message:
        response_dict["message"] = message

    return jsonify(response_dict), status_code


def handle_api_error(
    error_message: str,
    default_data: Any = None,
    status_code: int = 500,
    logger=None,
) -> Tuple[Dict, int]:
    """Create a standardized error response.

    Args:
        error_message: Error message to log and return
        default_data: Default data value on error (empty list, dict, etc.)
        status_code: HTTP status code (default: 500)
        logger: Logger instance (uses root logger if None)

    Returns:
        Tuple of (jsonify response, HTTP status code)

    Example:
        >>> response, code = handle_api_error(
        ...     "Database connection failed",
        ...     default_data=[],
        ...     status_code=503
        ... )
    """
    if default_data is None:
        default_data = {}

    if logger:
        logger.error(error_message)
    else:
        LoggingFactory.get_logger(__name__).error(error_message)

    return api_response(
        default_data, status="error", message=error_message, status_code=status_code
    )
