"""Unit tests for strategy components."""

import pytest

from src.strategies.factory import StrategyFactory


class TestStrategyFactory:
    """Test suite for StrategyFactory."""

    def test_strategy_factory_exists(self):
        """Test that StrategyFactory exists."""
        assert StrategyFactory is not None

    def test_strategy_factory_has_create_strategy_method(self):
        """Test that StrategyFactory has create_strategy method."""
        assert hasattr(StrategyFactory, "create_strategy")
        assert callable(getattr(StrategyFactory, "create_strategy"))

    def test_strategy_factory_create_ema(self):
        """Test creating EMA strategy."""
        mock_db = Mock()
        params = {}
        strategy = StrategyFactory.create_strategy("EMA", params, mock_db)
        assert strategy is not None

    def test_strategy_factory_create_sma(self):
        """Test creating SMA strategy."""
        mock_db = Mock()
        params = {}
        strategy = StrategyFactory.create_strategy("SMA", params, mock_db)
        assert strategy is not None

    def test_strategy_factory_create_macd(self):
        """Test creating MACD strategy."""
        mock_db = Mock()
        params = {}
        strategy = StrategyFactory.create_strategy("MACD", params, mock_db)
        assert strategy is not None

    def test_strategy_factory_create_rsi(self):
        """Test creating RSI strategy."""
        mock_db = Mock()
        params = {}
        strategy = StrategyFactory.create_strategy("RSI", params, mock_db)
        assert strategy is not None


class TestBaseStrategy:
    """Test suite for base strategy."""

    def test_base_strategy_import(self):
        """Test that BaseStrategy can be imported."""
        from src.core.base_strategy import BaseStrategy

        assert BaseStrategy is not None

    def test_base_strategy_is_abstract(self):
        """Test that BaseStrategy is abstract."""
        from src.core.base_strategy import BaseStrategy

        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            BaseStrategy()


class TestEMAStrategy:
    """Test suite for EMA strategy."""

    def test_ema_strategy_import(self):
        """Test that EMAStrategy can be imported."""
        from src.strategies.ema_strategy import EMAStrategy

        assert EMAStrategy is not None

    def test_ema_strategy_has_generate_entry_signal(self):
        """Test that EMAStrategy has generate_entry_signal method."""
        from src.strategies.ema_strategy import EMAStrategy

        assert hasattr(EMAStrategy, "generate_entry_signal")

    def test_ema_strategy_has_generate_exit_signal(self):
        """Test that EMAStrategy has generate_exit_signal method."""
        from src.strategies.ema_strategy import EMAStrategy

        assert hasattr(EMAStrategy, "generate_exit_signal")

    def test_ema_strategy_initialization(self):
        """Test EMAStrategy initialization."""
        from src.strategies.ema_strategy import EMAStrategy

        mock_db = Mock()
        params = {}
        config = {}
        strategy = EMAStrategy(params, mock_db, config)
        assert strategy is not None

    def test_ema_strategy_entry_signal_with_mock_data(self):
        """Test EMA entry signal method exists."""
        from src.strategies.ema_strategy import EMAStrategy

        mock_db = Mock()
        params = {"fast_ema": 12, "slow_ema": 26}
        config = {}
        strategy = EMAStrategy(params, mock_db, config)

        # Verify method exists and is callable
        assert callable(strategy.generate_entry_signal)

    def test_ema_strategy_exit_signal_with_mock_data(self):
        """Test EMA exit signal method exists."""
        from src.strategies.ema_strategy import EMAStrategy

        mock_db = Mock()
        params = {"fast_ema": 12, "slow_ema": 26}
        config = {}
        strategy = EMAStrategy(params, mock_db, config)

        # Verify method exists and is callable
        assert callable(strategy.generate_exit_signal)


class TestSMAStrategy:
    """Test suite for SMA strategy."""

    def test_sma_strategy_import(self):
        """Test that SMAStrategy can be imported."""
        from src.strategies.sma_strategy import SMAStrategy

        assert SMAStrategy is not None

    def test_sma_strategy_has_generate_entry_signal(self):
        """Test that SMAStrategy has generate_entry_signal method."""
        from src.strategies.sma_strategy import SMAStrategy

        assert hasattr(SMAStrategy, "generate_entry_signal")

    def test_sma_strategy_has_generate_exit_signal(self):
        """Test that SMAStrategy has generate_exit_signal method."""
        from src.strategies.sma_strategy import SMAStrategy

        assert hasattr(SMAStrategy, "generate_exit_signal")

    def test_sma_strategy_entry_signal_generation(self):
        """Test SMA entry signal method exists."""
        from src.strategies.sma_strategy import SMAStrategy

        mock_db = Mock()
        params = {"fast_sma": 10, "slow_sma": 20}
        config = {}
        strategy = SMAStrategy(params, mock_db, config)

        assert callable(strategy.generate_entry_signal)

    def test_sma_strategy_exit_signal_generation(self):
        """Test SMA exit signal method exists."""
        from src.strategies.sma_strategy import SMAStrategy

        mock_db = Mock()
        params = {"fast_sma": 10, "slow_sma": 20}
        config = {}
        strategy = SMAStrategy(params, mock_db, config)

        assert callable(strategy.generate_exit_signal)


class TestMACDStrategy:
    """Test suite for MACD strategy."""

    def test_macd_strategy_import(self):
        """Test that MACDStrategy can be imported."""
        from src.strategies.macd_strategy import MACDStrategy

        assert MACDStrategy is not None

    def test_macd_strategy_has_generate_entry_signal(self):
        """Test that MACDStrategy has generate_entry_signal method."""
        from src.strategies.macd_strategy import MACDStrategy

        assert hasattr(MACDStrategy, "generate_entry_signal")

    def test_macd_strategy_has_generate_exit_signal(self):
        """Test that MACDStrategy has generate_exit_signal method."""
        from src.strategies.macd_strategy import MACDStrategy

        assert hasattr(MACDStrategy, "generate_exit_signal")

    def test_macd_strategy_entry_signal_generation(self):
        """Test MACD entry signal method exists."""
        from src.strategies.macd_strategy import MACDStrategy

        mock_db = Mock()
        params = {"fast_period": 12, "slow_period": 26, "signal_period": 9}
        config = {}
        strategy = MACDStrategy(params, mock_db, config)

        assert callable(strategy.generate_entry_signal)

    def test_macd_strategy_exit_signal_generation(self):
        """Test MACD exit signal method exists."""
        from src.strategies.macd_strategy import MACDStrategy

        mock_db = Mock()
        params = {"fast_period": 12, "slow_period": 26, "signal_period": 9}
        config = {}
        strategy = MACDStrategy(params, mock_db, config)

        assert callable(strategy.generate_exit_signal)


class TestRSIStrategy:
    """Test suite for RSI strategy."""

    def test_rsi_strategy_import(self):
        """Test that RSIStrategy can be imported."""
        from src.strategies.rsi_strategy import RSIStrategy

        assert RSIStrategy is not None

    def test_rsi_strategy_has_generate_entry_signal(self):
        """Test that RSIStrategy has generate_entry_signal method."""
        from src.strategies.rsi_strategy import RSIStrategy

        assert hasattr(RSIStrategy, "generate_entry_signal")

    def test_rsi_strategy_has_generate_exit_signal(self):
        """Test that RSIStrategy has generate_exit_signal method."""
        from src.strategies.rsi_strategy import RSIStrategy

        assert hasattr(RSIStrategy, "generate_exit_signal")

    def test_rsi_strategy_entry_signal_generation(self):
        """Test RSI entry signal method exists."""
        from src.strategies.rsi_strategy import RSIStrategy

        mock_db = Mock()
        params = {"period": 14, "oversold": 30, "overbought": 70}
        config = {}
        strategy = RSIStrategy(params, mock_db, config)

        assert callable(strategy.generate_entry_signal)

    def test_rsi_strategy_exit_signal_generation(self):
        """Test RSI exit signal method exists."""
        from src.strategies.rsi_strategy import RSIStrategy

        mock_db = Mock()
        params = {"period": 14, "oversold": 30, "overbought": 70}
        config = {}
        strategy = RSIStrategy(params, mock_db, config)

        assert callable(strategy.generate_exit_signal)
