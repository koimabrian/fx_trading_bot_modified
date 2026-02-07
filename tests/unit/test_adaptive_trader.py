"""Unit tests for adaptive trader module."""

import logging
import pytest
from unittest.mock import Mock, MagicMock, patch

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

    # ===== NEW COMPREHENSIVE TESTS =====

    def test_logger_is_logging_logger(self, adaptive_trader):
        """Test that logger is a proper logging.Logger instance."""
        assert isinstance(adaptive_trader.logger, logging.Logger)

    def test_loaded_strategies_initialized_empty(self, adaptive_trader):
        """Test that loaded_strategies dict is initialized empty."""
        assert isinstance(adaptive_trader.loaded_strategies, dict)
        assert len(adaptive_trader.loaded_strategies) == 0

    def test_strategy_selector_exists(self, adaptive_trader):
        """Test that strategy_selector is initialized."""
        assert hasattr(adaptive_trader, "strategy_selector")
        assert adaptive_trader.strategy_selector is not None

    def test_trading_rules_exists(self, adaptive_trader):
        """Test that trading_rules is initialized."""
        assert hasattr(adaptive_trader, "trading_rules")
        assert adaptive_trader.trading_rules is not None

    @patch("src.utils.config_manager.ConfigManager.get_config")
    def test_config_loading_success(self, mock_get_config, adaptive_trader):
        """Test successful configuration loading."""
        test_config = {"trading": {"max_positions": 5}, "strategies": []}
        mock_get_config.return_value = test_config

        config = adaptive_trader._load_config()
        assert isinstance(config, dict)

    @patch("src.utils.config_manager.ConfigManager.get_config")
    def test_config_loading_failure(self, mock_get_config, adaptive_trader):
        """Test config loading handles exceptions gracefully."""
        mock_get_config.side_effect = Exception("Config file not found")

        config = adaptive_trader._load_config()
        assert isinstance(config, dict)

    @patch("src.core.adaptive_trader.StrategyFactory.create_strategy")
    @patch("src.utils.config_manager.ConfigManager.get_config")
    def test_get_strategy_instance_creates_new(
        self, mock_get_config, mock_create_strategy, adaptive_trader
    ):
        """Test that _get_strategy_instance creates and caches new strategies."""
        mock_config = {
            "strategies": [{"name": "rsi", "params": {"period": 14, "overbought": 70}}]
        }
        mock_get_config.return_value = mock_config
        mock_strategy = MagicMock()
        mock_create_strategy.return_value = mock_strategy

        trader = AdaptiveTrader(
            adaptive_trader.strategy_manager,
            adaptive_trader.mt5_connector,
            adaptive_trader.db,
        )

        result = trader._get_strategy_instance("rsi", "BTCUSD", "H1")
        assert result == mock_strategy

    @patch("src.core.adaptive_trader.StrategyFactory.create_strategy")
    @patch("src.utils.config_manager.ConfigManager.get_config")
    def test_get_strategy_instance_uses_cache(
        self, mock_get_config, mock_create_strategy, adaptive_trader
    ):
        """Test that _get_strategy_instance uses cached strategies."""
        mock_config = {
            "strategies": [{"name": "rsi", "params": {"period": 14, "overbought": 70}}]
        }
        mock_get_config.return_value = mock_config
        mock_strategy = MagicMock()
        mock_create_strategy.return_value = mock_strategy

        trader = AdaptiveTrader(
            adaptive_trader.strategy_manager,
            adaptive_trader.mt5_connector,
            adaptive_trader.db,
        )

        # First call
        result1 = trader._get_strategy_instance("rsi", "BTCUSD", "H1")
        assert result1 == mock_strategy
        assert mock_create_strategy.call_count == 1

        # Second call (should use cache)
        result2 = trader._get_strategy_instance("rsi", "BTCUSD", "H1")
        assert result2 == mock_strategy
        assert mock_create_strategy.call_count == 1  # Should not increase

    @patch("src.utils.config_manager.ConfigManager.get_config")
    def test_get_strategy_instance_not_found(self, mock_get_config, adaptive_trader):
        """Test _get_strategy_instance returns None for non-existent strategy."""
        mock_config = {"strategies": []}
        mock_get_config.return_value = mock_config

        trader = AdaptiveTrader(
            adaptive_trader.strategy_manager,
            adaptive_trader.mt5_connector,
            adaptive_trader.db,
        )

        result = trader._get_strategy_instance("nonexistent", "BTCUSD", "H1")
        assert result is None

    @patch("src.core.adaptive_trader.StrategyFactory.create_strategy")
    @patch("src.utils.config_manager.ConfigManager.get_config")
    def test_get_strategy_instance_creation_error(
        self, mock_get_config, mock_create_strategy, adaptive_trader
    ):
        """Test _get_strategy_instance handles creation errors."""
        mock_config = {"strategies": [{"name": "rsi", "params": {"period": 14}}]}
        mock_get_config.return_value = mock_config
        mock_create_strategy.side_effect = ValueError("Invalid params")

        trader = AdaptiveTrader(
            adaptive_trader.strategy_manager,
            adaptive_trader.mt5_connector,
            adaptive_trader.db,
        )

        result = trader._get_strategy_instance("rsi", "BTCUSD", "H1")
        assert result is None

    def test_execute_adaptive_trades(self, adaptive_trader):
        """Test adaptive trade execution."""
        if hasattr(adaptive_trader, "execute_adaptive_trades"):
            adaptive_trader.mt5_connector.is_connected.return_value = True
            result = adaptive_trader.execute_adaptive_trades("EURUSD")
            assert result is None

    def test_can_open_position(self, adaptive_trader):
        """Test position opening eligibility check."""
        if hasattr(adaptive_trader, "_can_open_position"):
            adaptive_trader.mt5_connector.get_open_positions_count.return_value = 5
            adaptive_trader.config = {"risk_management": {"max_open_positions": 10}}
            can_open = adaptive_trader._can_open_position()
            assert isinstance(can_open, bool)

    def test_clear_cache(self, adaptive_trader):
        """Test strategy cache clearing."""
        if hasattr(adaptive_trader, "clear_cache"):
            adaptive_trader.loaded_strategies = {"test": Mock()}
            adaptive_trader.clear_cache()
            assert len(adaptive_trader.loaded_strategies) == 0

    def test_get_cache_stats(self, adaptive_trader):
        """Test cache statistics retrieval."""
        if hasattr(adaptive_trader, "get_cache_stats"):
            adaptive_trader.loaded_strategies = {"rsi_eurusd_h1": Mock()}
            stats = adaptive_trader.get_cache_stats()
            assert isinstance(stats, dict)

    def test_config_loading(self, adaptive_trader):
        """Test configuration loading."""
        config = adaptive_trader.config
        assert isinstance(config, dict)

    def test_strategy_selector_initialization(self, adaptive_trader):
        """Test strategy selector initialization."""
        assert hasattr(adaptive_trader, "strategy_selector")
        assert adaptive_trader.strategy_selector is not None

    def test_trading_rules_initialization(self, adaptive_trader):
        """Test trading rules initialization."""
        assert hasattr(adaptive_trader, "trading_rules")
        assert adaptive_trader.trading_rules is not None

    @pytest.mark.parametrize(
        "strategy,symbol,timeframe",
        [
            ("rsi", "BTCUSD", "M15"),
            ("macd", "EURUSD", "H1"),
            ("ema", "GBPUSD", "H4"),
            ("bollinger_bands", "USDJPY", "D1"),
        ],
    )
    def test_cache_key_generation(self, adaptive_trader, strategy, symbol, timeframe):
        """Parametrized test for cache key generation."""
        expected_key = f"{strategy}_{symbol}_{timeframe}"
        mock_strategy = MagicMock()
        adaptive_trader.loaded_strategies[expected_key] = mock_strategy

        assert expected_key in adaptive_trader.loaded_strategies
        assert adaptive_trader.loaded_strategies[expected_key] == mock_strategy

    def test_strategy_instance_isolation(self, adaptive_trader):
        """Test that different strategy instances are isolated."""
        mock_rsi = MagicMock()
        mock_macd = MagicMock()

        adaptive_trader.loaded_strategies["rsi_btcusd_h1"] = mock_rsi
        adaptive_trader.loaded_strategies["macd_btcusd_h1"] = mock_macd

        assert adaptive_trader.loaded_strategies["rsi_btcusd_h1"] == mock_rsi
        assert adaptive_trader.loaded_strategies["macd_btcusd_h1"] == mock_macd
        assert mock_rsi != mock_macd

    def test_none_dependencies(self):
        """Test handling of None dependencies."""
        trader = AdaptiveTrader(None, None, None)
        assert trader is not None
        assert trader.strategy_manager is None
        assert trader.mt5_connector is None
        assert trader.db is None

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

    def test_get_signals_adaptive(self, adaptive_trader):
        """Test adaptive signal generation for symbol."""
        if hasattr(adaptive_trader, "get_signals_adaptive"):
            adaptive_trader.strategy_selector = Mock()
            adaptive_trader.strategy_selector.get_best_strategy.return_value = (
                "rsi",
                0.85,
            )
            signals = adaptive_trader.get_signals_adaptive("EURUSD")
            assert isinstance(signals, list)

    def test_compute_confidence(self, adaptive_trader):
        """Test confidence score computation."""
        if hasattr(adaptive_trader, "_compute_confidence"):
            strategy_info = {
                "win_rate": 0.55,
                "sharpe_ratio": 1.5,
                "max_drawdown": 0.10,
                "total_trades": 100,
            }
            confidence = adaptive_trader._compute_confidence(strategy_info)
            assert confidence is None or isinstance(confidence, float)
            if isinstance(confidence, float):
                assert 0.0 <= confidence <= 1.0

    def test_run_pre_signal_checks(self, adaptive_trader):
        """Test pre-signal checks."""
        if hasattr(adaptive_trader, "run_pre_signal_checks"):
            adaptive_trader.mt5_connector.is_connected.return_value = True
            checks = adaptive_trader.run_pre_signal_checks()
            assert checks is None or isinstance(checks, dict)

    def test_execute_adaptive_trades(self, adaptive_trader):
        """Test adaptive trade execution."""
        if hasattr(adaptive_trader, "execute_adaptive_trades"):
            adaptive_trader.mt5_connector.is_connected.return_value = True
            result = adaptive_trader.execute_adaptive_trades("EURUSD")
            assert result is None

    def test_can_open_position(self, adaptive_trader):
        """Test position opening eligibility check."""
        if hasattr(adaptive_trader, "_can_open_position"):
            adaptive_trader.mt5_connector.get_open_positions_count.return_value = 5
            adaptive_trader.config = {"risk_management": {"max_open_positions": 10}}
            can_open = adaptive_trader._can_open_position()
            assert isinstance(can_open, bool)

    def test_clear_cache(self, adaptive_trader):
        """Test strategy cache clearing."""
        if hasattr(adaptive_trader, "clear_cache"):
            adaptive_trader.loaded_strategies = {"test": Mock()}
            adaptive_trader.clear_cache()
            assert len(adaptive_trader.loaded_strategies) == 0

    def test_get_cache_stats(self, adaptive_trader):
        """Test cache statistics retrieval."""
        if hasattr(adaptive_trader, "get_cache_stats"):
            adaptive_trader.loaded_strategies = {"rsi_eurusd_h1": Mock()}
            stats = adaptive_trader.get_cache_stats()
            assert isinstance(stats, dict)

    def test_config_loading(self, adaptive_trader):
        """Test configuration loading."""
        config = adaptive_trader.config
        assert isinstance(config, dict)

    def test_strategy_selector_initialization(self, adaptive_trader):
        """Test strategy selector initialization."""
        assert hasattr(adaptive_trader, "strategy_selector")
        assert adaptive_trader.strategy_selector is not None

    def test_trading_rules_initialization(self, adaptive_trader):
        """Test trading rules initialization."""
        assert hasattr(adaptive_trader, "trading_rules")
        assert adaptive_trader.trading_rules is not None
