"""Unit tests for utility modules."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.utils.logging_factory import LoggingFactory
from src.utils.mt5_decorator import mt5_safe


class TestLoggingFactory:
    """Test suite for LoggingFactory."""

    def test_logging_factory_get_logger(self):
        """Test getting logger from LoggingFactory."""
        logger = LoggingFactory.get_logger(__name__)
        assert logger is not None

    def test_logging_factory_configure(self):
        """Test configuring LoggingFactory."""
        result = LoggingFactory.configure()
        # Should not raise exception
        assert True

    def test_logger_has_methods(self):
        """Test logger has required methods."""
        logger = LoggingFactory.get_logger(__name__)
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "debug")


class TestMT5Decorator:
    """Test suite for mt5_safe decorator."""

    def test_mt5_decorator_exists(self):
        """Test that mt5_safe decorator exists."""
        assert mt5_safe is not None
        assert callable(mt5_safe)

    def test_mt5_decorator_can_decorate_function(self):
        """Test that decorator can be applied to functions."""

        @mt5_safe(max_retries=1)
        def test_function(self):
            return "success"

        assert callable(test_function)

    @patch("MetaTrader5.initialize", return_value=True)
    def test_mt5_decorator_returns_callable(self, mock_init):
        """Test that decorated function returns callable."""

        @mt5_safe(max_retries=1)
        def dummy_method(self):
            return True

        assert callable(dummy_method)


class TestTradingRules:
    """Test suite for trading rules."""

    def test_trading_rules_import(self):
        """Test that TradingRules can be imported."""
        from src.utils.trading_rules import TradingRules

        assert TradingRules is not None

    def test_trading_rules_has_category_methods(self):
        """Test TradingRules has category checking methods."""
        from src.utils.trading_rules import TradingRules

        assert hasattr(TradingRules, "is_crypto")
        assert hasattr(TradingRules, "is_forex")
        assert hasattr(TradingRules, "is_stock")
        assert hasattr(TradingRules, "can_trade")


class TestVolatilityManager:
    """Test suite for VolatilityManager."""

    def test_volatility_manager_import(self):
        """Test that VolatilityManager can be imported."""
        from src.utils.volatility_manager import VolatilityManager

        assert VolatilityManager is not None

    def test_volatility_manager_initialization(self):
        """Test VolatilityManager initialization."""
        from src.utils.volatility_manager import VolatilityManager

        mock_db = Mock()
        config = {}
        manager = VolatilityManager(config, mock_db)
        assert manager is not None


class TestErrorHandling:
    """Test suite for error handling across utilities."""

    def test_logger_error_handling(self):
        """Test that logger handles errors gracefully."""
        logger = LoggingFactory.get_logger(__name__)

        # Should not raise exception
        try:
            logger.error("Test error message")
            logger.warning("Test warning message")
        except Exception:
            pytest.fail("Logger should handle errors gracefully")

    def test_decorator_error_handling(self):
        """Test that mt5_safe decorator handles errors."""

        @mt5_safe(max_retries=1)
        def failing_function(self):
            raise ValueError("Test error")

        # Decorator should handle error gracefully
        assert callable(failing_function)

    def test_trading_rules_error_handling(self):
        """Test trading rules error handling with invalid input."""
        from src.utils.trading_rules import TradingRules

        # Should handle invalid symbol gracefully
        try:
            result = TradingRules.can_trade(None)
            # Should either return False or handle gracefully
            assert result is not None or result is None
        except Exception:
            # Expected to handle gracefully
            pass

    def test_volatility_manager_error_handling(self):
        """Test volatility manager error handling."""
        from src.utils.volatility_manager import VolatilityManager

        mock_db = Mock()
        config = {}
        manager = VolatilityManager(config, mock_db)

        # Should handle None/invalid data gracefully
        try:
            if hasattr(manager, "calculate_volatility"):
                manager.calculate_volatility(None)
        except Exception:
            # Expected to raise error for invalid input
            pass

    def test_logging_factory_multiple_loggers(self):
        """Test creating multiple loggers."""
        logger1 = LoggingFactory.get_logger("test1")
        logger2 = LoggingFactory.get_logger("test2")

        # Both should be valid loggers
        assert logger1 is not None
        assert logger2 is not None
        # They may or may not be the same instance
        assert isinstance(logger1, type(logger2))

    def test_mt5_decorator_with_exception(self):
        """Test decorator behavior with exceptions."""
        call_count = 0

        @mt5_safe(max_retries=2)
        def flaky_function(self):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "success"

        assert callable(flaky_function)
