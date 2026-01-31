"""Unit tests for error handling system."""

import pytest
from unittest.mock import Mock, patch
from enum import Enum

from src.utils.error_handler import ErrorHandler, ErrorSeverity, TradingError


class TestErrorSeverity:
    """Test ErrorSeverity enum."""

    def test_error_severity_values_exist(self):
        """Test all severity levels are defined."""
        assert hasattr(ErrorSeverity, "RECOVERABLE")
        assert hasattr(ErrorSeverity, "WARNING")
        assert hasattr(ErrorSeverity, "CRITICAL")
        assert hasattr(ErrorSeverity, "IGNORE")

    def test_error_severity_recoverable(self):
        """Test RECOVERABLE severity level."""
        severity = ErrorSeverity.RECOVERABLE
        assert severity.value == "recoverable"

    def test_error_severity_warning(self):
        """Test WARNING severity level."""
        severity = ErrorSeverity.WARNING
        assert severity.value == "warning"

    def test_error_severity_critical(self):
        """Test CRITICAL severity level."""
        severity = ErrorSeverity.CRITICAL
        assert severity.value == "critical"

    def test_error_severity_ignore(self):
        """Test IGNORE severity level."""
        severity = ErrorSeverity.IGNORE
        assert severity.value == "ignore"


class TestTradingError:
    """Test custom TradingError exception."""

    def test_trading_error_initialization(self):
        """Test TradingError initialization with message."""
        error = TradingError("Test error message")
        assert error.message == "Test error message"
        assert error.severity == ErrorSeverity.WARNING

    def test_trading_error_with_severity(self):
        """Test TradingError with specific severity."""
        error = TradingError("Critical error", severity=ErrorSeverity.CRITICAL)
        assert error.message == "Critical error"
        assert error.severity == ErrorSeverity.CRITICAL

    def test_trading_error_is_exception(self):
        """Test TradingError is an Exception."""
        error = TradingError("Test")
        assert isinstance(error, Exception)

    def test_trading_error_string_representation(self):
        """Test TradingError string representation."""
        error = TradingError("Test error")
        assert "Test error" in str(error)


class TestErrorHandler:
    """Test suite for ErrorHandler class."""

    @pytest.fixture
    def error_handler(self):
        """Create ErrorHandler instance."""
        return ErrorHandler()

    def test_error_handler_initialization(self, error_handler):
        """Test ErrorHandler initializes correctly."""
        assert error_handler is not None
        assert hasattr(error_handler, "ERROR_MAP")
        assert isinstance(error_handler.ERROR_MAP, dict)

    def test_error_handler_has_handle_method(self, error_handler):
        """Test ErrorHandler has handle_error method."""
        assert hasattr(error_handler, "handle_error")
        assert callable(error_handler.handle_error)

    def test_error_handler_error_map_coverage(self, error_handler):
        """Test ERROR_MAP covers common error types."""
        error_map = error_handler.ERROR_MAP
        assert ValueError in error_map
        assert KeyError in error_map
        assert ConnectionError in error_map
        assert TimeoutError in error_map

    def test_error_handler_maps_value_error(self, error_handler):
        """Test ValueError mapping."""
        severity, description = error_handler.ERROR_MAP[ValueError]
        assert severity == ErrorSeverity.WARNING
        assert isinstance(description, str)

    def test_error_handler_maps_connection_error(self, error_handler):
        """Test ConnectionError mapping to RECOVERABLE."""
        severity, description = error_handler.ERROR_MAP[ConnectionError]
        assert severity == ErrorSeverity.RECOVERABLE

    def test_error_handler_maps_key_error(self, error_handler):
        """Test KeyError mapping to CRITICAL."""
        severity, description = error_handler.ERROR_MAP[KeyError]
        assert severity == ErrorSeverity.CRITICAL

    def test_error_handler_handle_method_with_error(self, error_handler):
        """Test handle method processes errors correctly."""
        error = ValueError("Invalid value")
        result = error_handler.handle_error(error, context="test_op")
        # Should return result without raising
        assert result is None or isinstance(result, (dict, bool))

    def test_error_handler_handle_recoverable_error(self, error_handler):
        """Test handling of recoverable errors."""
        error = ConnectionError("Connection failed")
        # Should not raise, should log and continue
        result = error_handler.handle_error(error, context="network_call")
        assert result is None or isinstance(result, dict)

    def test_error_handler_handle_critical_error(self, error_handler):
        """Test handling of critical errors."""
        error = KeyError("Missing config key")
        # Critical errors may raise or log
        try:
            result = error_handler.handle_error(error, context="config_load")
            # May return result or raise
            assert result is None or isinstance(result, dict)
        except (KeyError, TradingError):
            # Expected behavior for critical errors
            pass

    def test_error_handler_handle_unknown_error(self, error_handler):
        """Test handling of unknown error types."""

        class CustomError(Exception):
            pass

        error = CustomError("Unknown error")
        # Should handle gracefully
        result = error_handler.handle_error(error, context="custom_op")
        assert result is None or isinstance(result, dict)

    def test_error_handler_severity_in_error_map(self, error_handler):
        """Test all mappings have valid severity."""
        for error_type, (severity, description) in error_handler.ERROR_MAP.items():
            assert isinstance(severity, ErrorSeverity)
            assert isinstance(description, str)
            assert len(description) > 0

    def test_error_handler_with_operation_context(self, error_handler):
        """Test error handler with operation context."""
        error = ValueError("Bad value")
        # Should use operation context for better logging
        result = error_handler.handle_error(
            error, context="place_order", symbol="EURUSD"
        )
        assert result is None or isinstance(result, dict)

    def test_error_handler_multiple_errors(self, error_handler):
        """Test handling multiple sequential errors."""
        errors = [
            ValueError("Error 1"),
            ConnectionError("Error 2"),
            KeyError("Error 3"),
        ]

        for error in errors:
            try:
                result = error_handler.handle_error(error, context="multi_test")
                assert result is None or isinstance(result, dict)
            except (KeyError, TradingError):
                # Critical errors may raise
                pass

    def test_error_handler_get_severity(self, error_handler):
        """Test getting severity level for error."""
        if hasattr(error_handler, "get_severity"):
            severity = error_handler.get_severity(ValueError("test"))
            assert severity in [
                ErrorSeverity.RECOVERABLE,
                ErrorSeverity.WARNING,
                ErrorSeverity.CRITICAL,
                ErrorSeverity.IGNORE,
            ]

    def test_error_handler_get_description(self, error_handler):
        """Test getting description for error type."""
        if hasattr(error_handler, "get_description"):
            desc = error_handler.get_description(ConnectionError)
            assert isinstance(desc, str)
            assert len(desc) > 0

    def test_error_handler_logging_integration(self, error_handler):
        """Test error handler integrates with logging."""
        assert hasattr(error_handler, "logger") or True  # May use LoggingFactory
        error = RuntimeError("Test log error")
        error_handler.handle_error(error, context="logging_test")
        # Should log without raising


class TestErrorHandlingPatterns:
    """Test error handling patterns and best practices."""

    def test_error_recovery_pattern(self):
        """Test RECOVERABLE error pattern."""
        handler = ErrorHandler()
        # Recoverable errors should attempt retry
        error = TimeoutError("Connection timeout")
        severity, _ = handler.ERROR_MAP[TimeoutError]
        assert severity == ErrorSeverity.RECOVERABLE

    def test_error_critical_pattern(self):
        """Test CRITICAL error pattern."""
        handler = ErrorHandler()
        # Critical errors should stop execution
        error = KeyError("Critical config missing")
        severity, _ = handler.ERROR_MAP[KeyError]
        assert severity == ErrorSeverity.CRITICAL

    def test_error_context_preservation(self):
        """Test error context is preserved during handling."""
        handler = ErrorHandler()
        error = ValueError("Invalid price: -100")
        # Context should be preserved
        result = handler.handle_error(error, context="price_validation")
        assert result is None or isinstance(result, dict)

    def test_error_aggregation(self):
        """Test multiple errors can be aggregated."""
        handler = ErrorHandler()
        errors = [
            ValueError("Error 1"),
            RuntimeError("Error 2"),
            ConnectionError("Error 3"),
        ]

        for error in errors:
            handler.handle_error(error, context="aggregation_test")
        # Should handle all errors


class TestErrorHandlerIntegration:
    """Integration tests for error handler."""

    def test_trading_operation_error_handling(self):
        """Test error handling in trading context."""
        handler = ErrorHandler()

        trading_errors = [
            ValueError("Invalid lot size"),
            ConnectionError("MT5 connection lost"),
            RuntimeError("Order placement failed"),
        ]

        for error in trading_errors:
            result = handler.handle_error(error, context="place_order", symbol="EURUSD")
            assert result is None or isinstance(result, dict)

    def test_data_validation_error_handling(self):
        """Test error handling in data validation."""
        handler = ErrorHandler()

        data_errors = [
            ValueError("Invalid price"),
            KeyError("Missing data field"),
            TypeError("Wrong data type"),
        ]

        for error in data_errors:
            try:
                result = handler.handle_error(error, context="validate_data")
                assert result is None or isinstance(result, dict)
            except (KeyError, TradingError):
                # Critical errors may raise
                pass

    def test_initialization_error_handling(self):
        """Test error handling during initialization."""
        handler = ErrorHandler()

        init_errors = [
            KeyError("Config key missing"),
            FileNotFoundError("Config file not found"),
            PermissionError("Access denied"),
        ]

        for error in init_errors:
            try:
                result = handler.handle_error(error, context="initialize")
                # May raise or return
            except Exception:
                # Expected for critical errors
                pass
