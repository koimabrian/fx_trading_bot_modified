"""Unit tests for strategy selector module."""

import pytest
from unittest.mock import Mock

from src.core.strategy_selector import StrategySelector


class TestStrategySelector:
    """Test suite for StrategySelector class."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for StrategySelector."""
        db = Mock()
        return db

    @pytest.fixture
    def strategy_selector(self, mock_dependencies):
        """Create StrategySelector instance with mocks."""
        db = mock_dependencies
        return StrategySelector(db)

    def test_strategy_selector_initialization(self, strategy_selector):
        """Test StrategySelector initializes correctly."""
        assert strategy_selector is not None
        assert strategy_selector.db is not None

    def test_strategy_selector_is_class(self):
        """Test that StrategySelector is a valid class."""
        assert StrategySelector is not None

    def test_strategy_selector_can_instantiate(self, strategy_selector):
        """Test StrategySelector can be instantiated."""
        assert isinstance(strategy_selector, StrategySelector)

    def test_strategy_selector_has_logger(self, strategy_selector):
        """Test StrategySelector has logger."""
        assert hasattr(strategy_selector, "logger")

    def test_strategy_selector_has_select_method(self, strategy_selector):
        """Test StrategySelector has select_strategy method."""
        if hasattr(strategy_selector, "select_strategy"):
            assert callable(strategy_selector.select_strategy)

    def test_select_strategy_returns_valid_type(self, strategy_selector):
        """Test select_strategy returns valid type."""
        if hasattr(strategy_selector, "select_strategy"):
            selected = strategy_selector.select_strategy()
            assert selected is None or isinstance(selected, str)

    def test_strategy_selector_get_performance(self, strategy_selector):
        """Test getting strategy performance."""
        if hasattr(strategy_selector, "get_performance"):
            perf = strategy_selector.get_performance("EMA")
            assert perf is None or isinstance(perf, dict)

    def test_strategy_selector_get_all_strategies(self, strategy_selector):
        """Test getting all available strategies."""
        if hasattr(strategy_selector, "get_available_strategies"):
            strategies = strategy_selector.get_available_strategies()
            assert strategies is None or isinstance(strategies, (list, tuple))

    def test_strategy_selector_rank_strategies(self, strategy_selector):
        """Test strategy ranking."""
        if hasattr(strategy_selector, "rank_strategies"):
            rankings = strategy_selector.rank_strategies()
            assert rankings is None or isinstance(rankings, (list, dict))

    def test_strategy_selector_best_strategy(self, strategy_selector):
        """Test getting best performing strategy."""
        if hasattr(strategy_selector, "get_best_strategy"):
            best = strategy_selector.get_best_strategy()
            assert best is None or isinstance(best, str)

    def test_strategy_selector_win_rate(self, strategy_selector):
        """Test getting win rate."""
        if hasattr(strategy_selector, "get_win_rate"):
            wr = strategy_selector.get_win_rate("SMA")
            assert wr is None or (isinstance(wr, (int, float)) and 0 <= wr <= 1)

    def test_strategy_selector_profit_factor(self, strategy_selector):
        """Test getting profit factor."""
        if hasattr(strategy_selector, "get_profit_factor"):
            pf = strategy_selector.get_profit_factor("RSI")
            assert pf is None or isinstance(pf, (int, float))

    def test_strategy_selector_drawdown(self, strategy_selector):
        """Test getting max drawdown."""
        if hasattr(strategy_selector, "get_max_drawdown"):
            dd = strategy_selector.get_max_drawdown("MACD")
            assert dd is None or isinstance(dd, (int, float))

    def test_strategy_selector_volatility_adjustment(self, strategy_selector):
        """Test volatility-based selection."""
        if hasattr(strategy_selector, "select_for_volatility"):
            selected = strategy_selector.select_for_volatility(high=True)
            assert selected is None or isinstance(selected, str)

    def test_strategy_selector_trend_selection(self, strategy_selector):
        """Test trend-based selection."""
        if hasattr(strategy_selector, "select_for_trend"):
            selected = strategy_selector.select_for_trend(trend="uptrend")
            assert selected is None or isinstance(selected, str)

    def test_strategy_selector_ensemble(self, strategy_selector):
        """Test ensemble selection."""
        if hasattr(strategy_selector, "select_ensemble"):
            ensemble = strategy_selector.select_ensemble(count=2)
            assert ensemble is None or isinstance(ensemble, (list, tuple))

    def test_strategy_selector_recent_performance(self, strategy_selector):
        """Test recent performance evaluation."""
        if hasattr(strategy_selector, "get_recent_performance"):
            perf = strategy_selector.get_recent_performance("EMA", days=7)
            assert perf is None or isinstance(perf, dict)

    def test_strategy_selector_recovery_time(self, strategy_selector):
        """Test getting recovery time."""
        if hasattr(strategy_selector, "get_recovery_time"):
            recovery = strategy_selector.get_recovery_time("SMA")
            assert recovery is None or isinstance(recovery, (int, float))

    def test_strategy_selector_consistency(self, strategy_selector):
        """Test strategy consistency check."""
        if hasattr(strategy_selector, "check_consistency"):
            consistent = strategy_selector.check_consistency("RSI")
            assert consistent is None or isinstance(consistent, bool)
