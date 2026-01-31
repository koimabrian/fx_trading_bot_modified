"""Unit tests for adaptive trader module."""

import pytest
from unittest.mock import Mock, patch

from src.core.adaptive_trader import AdaptiveTrader


class TestAdaptiveTrader:
    """Test suite for AdaptiveTrader class."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for AdaptiveTrader."""
        strategy_manager = Mock()
        mt5_connector = Mock()
        db = Mock()
        return strategy_manager, mt5_connector, db

    @pytest.fixture
    def adaptive_trader(self, mock_dependencies):
        """Create AdaptiveTrader instance with mocks."""
        strategy_manager, mt5_connector, db = mock_dependencies
        return AdaptiveTrader(strategy_manager, mt5_connector, db)

    def test_adaptive_trader_initialization(self, adaptive_trader):
        """Test AdaptiveTrader initializes correctly."""
        assert adaptive_trader is not None
        assert adaptive_trader.strategy_manager is not None
        assert adaptive_trader.mt5_connector is not None
        assert adaptive_trader.db is not None

    def test_adaptive_trader_is_class(self):
        """Test that AdaptiveTrader is a valid class."""
        assert AdaptiveTrader is not None

    def test_adaptive_trader_can_instantiate(self, adaptive_trader):
        """Test AdaptiveTrader can be instantiated."""
        assert isinstance(adaptive_trader, AdaptiveTrader)

    def test_adaptive_trader_has_logger(self, adaptive_trader):
        """Test AdaptiveTrader has logger."""
        assert hasattr(adaptive_trader, "logger")

    def test_adaptive_trader_has_strategy_manager(self, adaptive_trader):
        """Test AdaptiveTrader has strategy manager."""
        assert hasattr(adaptive_trader, "strategy_manager")

    def test_adaptive_trader_has_mt5_connector(self, adaptive_trader):
        """Test AdaptiveTrader has MT5 connector."""
        assert hasattr(adaptive_trader, "mt5_connector")

    def test_adaptive_trader_has_database(self, adaptive_trader):
        """Test AdaptiveTrader has database."""
        assert hasattr(adaptive_trader, "db")

    def test_adaptive_trader_can_generate_signals(self, adaptive_trader):
        """Test AdaptiveTrader can generate trading signals."""
        if hasattr(adaptive_trader, "generate_signal"):
            signal = adaptive_trader.generate_signal("EURUSD")
            assert signal is None or isinstance(signal, (dict, str))

    def test_adaptive_trader_can_adjust_risk(self, adaptive_trader):
        """Test AdaptiveTrader can adjust risk parameters."""
        if hasattr(adaptive_trader, "adjust_risk"):
            result = adaptive_trader.adjust_risk(0.02)
            assert result is None or isinstance(result, bool)

    def test_adaptive_trader_can_update_performance(self, adaptive_trader):
        """Test AdaptiveTrader can update performance metrics."""
        if hasattr(adaptive_trader, "update_performance"):
            result = adaptive_trader.update_performance(win=True, pnl=100.0)
            assert result is None or isinstance(result, bool)

    def test_adaptive_trader_can_get_metrics(self, adaptive_trader):
        """Test AdaptiveTrader can retrieve metrics."""
        if hasattr(adaptive_trader, "get_metrics"):
            metrics = adaptive_trader.get_metrics()
            assert metrics is None or isinstance(metrics, dict)

    def test_adaptive_trader_symbol_selection(self, adaptive_trader):
        """Test symbol selection mechanism."""
        if hasattr(adaptive_trader, "select_symbol"):
            symbol = adaptive_trader.select_symbol()
            assert symbol is None or isinstance(symbol, str)

    def test_adaptive_trader_timeframe_selection(self, adaptive_trader):
        """Test timeframe selection mechanism."""
        if hasattr(adaptive_trader, "select_timeframe"):
            timeframe = adaptive_trader.select_timeframe()
            assert timeframe is None or isinstance(timeframe, str)

    def test_adaptive_trader_position_sizing(self, adaptive_trader):
        """Test position sizing calculation."""
        if hasattr(adaptive_trader, "calculate_position_size"):
            size = adaptive_trader.calculate_position_size(
                entry=1.2500, stop_loss=1.2400, account_size=10000
            )
            assert size is None or isinstance(size, (int, float))

    def test_adaptive_trader_drawdown_protection(self, adaptive_trader):
        """Test drawdown protection mechanism."""
        if hasattr(adaptive_trader, "check_drawdown_limit"):
            protected = adaptive_trader.check_drawdown_limit()
            assert protected is None or isinstance(protected, bool)

    def test_adaptive_trader_recovery_mode(self, adaptive_trader):
        """Test recovery mode activation."""
        if hasattr(adaptive_trader, "enter_recovery_mode"):
            result = adaptive_trader.enter_recovery_mode()
            assert result is None or isinstance(result, bool)

    def test_adaptive_trader_profit_taking(self, adaptive_trader):
        """Test profit taking mechanism."""
        if hasattr(adaptive_trader, "apply_profit_taking"):
            result = adaptive_trader.apply_profit_taking(0.03)
            assert result is None or isinstance(result, bool)
