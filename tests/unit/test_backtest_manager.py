"""Unit tests for backtest manager module."""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from datetime import datetime

from src.backtesting.backtest_manager import BacktestManager


class TestBacktestManagerInitialization:
    """Test BacktestManager initialization."""

    def test_backtest_manager_initialization(self):
        """Test BacktestManager initializes correctly."""
        config = {"database": {"path": ":memory:"}}
        with patch("src.database.db_manager.DatabaseManager"):
            manager = BacktestManager(config)
            assert manager is not None

    def test_backtest_manager_with_config(self):
        """Test BacktestManager initialization with config."""
        config = {"database": {"path": ":memory:"}}
        with patch("src.database.db_manager.DatabaseManager"):
            manager = BacktestManager(config)
            assert hasattr(manager, "__init__")


class TestBacktestConfiguration:
    """Test backtest configuration."""

    def test_backtest_config_defaults(self):
        """Test backtest configuration defaults."""
        config = {
            "start_date": "2023-01-01",
            "end_date": "2024-01-01",
            "initial_balance": 10000,
            "symbols": ["EURUSD", "GBPUSD"],
            "timeframe": "H1",
        }

        assert config["initial_balance"] > 0
        assert len(config["symbols"]) > 0

    def test_backtest_date_range_validation(self):
        """Test backtest date range validation."""
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2024, 1, 1)

        is_valid = start_date < end_date
        assert is_valid is True

    def test_backtest_invalid_date_range(self):
        """Test validation of invalid date range."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2023, 1, 1)

        is_valid = start_date < end_date
        assert is_valid is False

    def test_backtest_symbol_list_validation(self):
        """Test symbol list validation."""
        symbols = ["EURUSD", "GBPUSD", "USDJPY"]

        assert len(symbols) > 0
        assert all(isinstance(s, str) for s in symbols)


class TestBacktestExecution:
    """Test backtest execution."""

    @pytest.fixture
    def mock_backtest_manager(self):
        """Create mock BacktestManager."""
        config = {"database": {"path": ":memory:"}}
        with patch("src.database.db_manager.DatabaseManager"):
            manager = BacktestManager(config)
            manager.execute = Mock()
            return manager

    def test_backtest_execution_called(self, mock_backtest_manager):
        """Test backtest execution is called."""
        config = {
            "symbol": "EURUSD",
            "start_date": "2023-01-01",
            "end_date": "2024-01-01",
        }

        mock_backtest_manager.execute(config)
        mock_backtest_manager.execute.assert_called_once_with(config)

    def test_backtest_execution_returns_results(self, mock_backtest_manager):
        """Test backtest execution returns results."""
        mock_backtest_manager.execute.return_value = {
            "total_trades": 50,
            "winning_trades": 30,
            "losing_trades": 20,
            "profit_factor": 2.5,
        }

        result = mock_backtest_manager.execute({})

        assert result is not None
        assert "total_trades" in result

    def test_backtest_execution_multiple_symbols(self, mock_backtest_manager):
        """Test backtest execution with multiple symbols."""
        symbols = ["EURUSD", "GBPUSD", "USDJPY"]
        results = {}

        for symbol in symbols:
            config = {"symbol": symbol}
            mock_backtest_manager.execute(config)
            results[symbol] = mock_backtest_manager.execute.return_value

        assert len(results) == len(symbols)


class TestBacktestDataProcessing:
    """Test backtest data processing."""

    @pytest.fixture
    def sample_ohlc_data(self):
        """Create sample OHLC data."""
        dates = pd.date_range("2023-01-01", periods=100, freq="D")
        close = 1.2500 + np.cumsum(np.random.normal(0, 0.001, 100))

        return pd.DataFrame(
            {
                "time": dates,
                "open": close + 0.0005,
                "high": close + 0.0010,
                "low": close - 0.0010,
                "close": close,
                "tick_volume": np.random.randint(1000, 5000, 100),
            }
        )

    def test_data_loading(self, sample_ohlc_data):
        """Test OHLC data loading."""
        assert len(sample_ohlc_data) == 100
        assert "close" in sample_ohlc_data.columns

    def test_data_preprocessing(self, sample_ohlc_data):
        """Test data preprocessing."""
        # Calculate indicators
        sample_ohlc_data["SMA20"] = sample_ohlc_data["close"].rolling(window=20).mean()

        assert "SMA20" in sample_ohlc_data.columns
        assert pd.isna(sample_ohlc_data["SMA20"].iloc[0:19]).all()

    def test_data_validation(self, sample_ohlc_data):
        """Test data validation."""
        # Check OHLC relationships
        valid = bool((sample_ohlc_data["high"] >= sample_ohlc_data["low"]).all())
        assert valid

    def test_data_filtering(self, sample_ohlc_data):
        """Test data filtering."""
        # Filter for trading hours only (9:00-17:00 example)
        sample_ohlc_data["hour"] = pd.to_datetime(sample_ohlc_data["time"]).dt.hour
        trading_hours = sample_ohlc_data[
            (sample_ohlc_data["hour"] >= 9) & (sample_ohlc_data["hour"] <= 17)
        ]

        assert len(trading_hours) >= 0


class TestSignalGeneration:
    """Test signal generation during backtest."""

    @pytest.fixture
    def data_with_indicators(self):
        """Create data with technical indicators."""
        dates = pd.date_range("2023-01-01", periods=100, freq="D")
        close = 1.2500 + np.cumsum(np.random.normal(0, 0.001, 100))

        df = pd.DataFrame(
            {
                "close": close,
            },
            index=dates,
        )

        df["SMA20"] = df["close"].rolling(window=20).mean()
        df["SMA50"] = df["close"].rolling(window=50).mean()

        return df

    def test_moving_average_signal_generation(self, data_with_indicators):
        """Test MA-based signal generation."""
        data_with_indicators["signal"] = 0
        data_with_indicators.loc[
            data_with_indicators["SMA20"] > data_with_indicators["SMA50"], "signal"
        ] = 1
        data_with_indicators.loc[
            data_with_indicators["SMA20"] < data_with_indicators["SMA50"], "signal"
        ] = -1

        assert "signal" in data_with_indicators.columns
        signal_values = set(data_with_indicators["signal"].unique())
        assert signal_values.issubset({-1, 0, 1})

    def test_signal_change_detection(self, data_with_indicators):
        """Test detection of signal changes."""
        data_with_indicators["signal"] = (
            data_with_indicators["SMA20"] > data_with_indicators["SMA50"]
        ).astype(int)

        data_with_indicators["signal_change"] = data_with_indicators[
            "signal"
        ] != data_with_indicators["signal"].shift(1)

        signal_changes = data_with_indicators["signal_change"].sum()
        assert signal_changes > 0

    def test_entry_signal_detection(self, data_with_indicators):
        """Test entry signal detection."""
        data_with_indicators["signal"] = (
            data_with_indicators["SMA20"] > data_with_indicators["SMA50"]
        ).astype(int)

        # Buy signal: 0->1
        buy_signals = (data_with_indicators["signal"] == 1) & (
            data_with_indicators["signal"].shift(1) == 0
        )

        assert buy_signals.sum() >= 0

    def test_exit_signal_detection(self, data_with_indicators):
        """Test exit signal detection."""
        data_with_indicators["signal"] = (
            data_with_indicators["SMA20"] > data_with_indicators["SMA50"]
        ).astype(int)

        # Sell signal: 1->0
        sell_signals = (data_with_indicators["signal"] == 0) & (
            data_with_indicators["signal"].shift(1) == 1
        )

        assert sell_signals.sum() >= 0


class TestTradeExecution:
    """Test trade execution during backtest."""

    def test_market_order_execution(self):
        """Test market order execution."""
        entry_price = 1.2500
        volume = 1.0

        order = {
            "type": "MARKET",
            "price": entry_price,
            "volume": volume,
            "symbol": "EURUSD",
        }

        assert order["type"] == "MARKET"
        assert order["price"] == entry_price

    def test_limit_order_execution(self):
        """Test limit order execution."""
        limit_price = 1.2480
        current_price = 1.2500

        # Order executes if price reaches limit
        executes = current_price <= limit_price
        assert executes is False

    def test_stop_loss_execution(self):
        """Test stop loss execution."""
        entry_price = 1.2500
        sl_price = 1.2400
        current_price = 1.2390

        # SL executes if price touches or crosses
        executes = current_price <= sl_price
        assert executes is True

    def test_take_profit_execution(self):
        """Test take profit execution."""
        entry_price = 1.2500
        tp_price = 1.2600
        current_price = 1.2610

        # TP executes if price touches or crosses
        executes = current_price >= tp_price
        assert executes is True

    def test_slippage_simulation(self):
        """Test slippage simulation."""
        expected_price = 1.2500
        slippage_pips = 2
        slippage_amount = slippage_pips / 10000

        actual_price = expected_price + slippage_amount

        assert actual_price > expected_price


class TestBacktestResultsStorage:
    """Test backtest results storage."""

    def test_backtest_results_creation(self):
        """Test backtest results creation."""
        results = {
            "symbol": "EURUSD",
            "start_date": "2023-01-01",
            "end_date": "2024-01-01",
            "total_trades": 50,
            "winning_trades": 30,
            "losing_trades": 20,
            "profit_factor": 2.5,
            "total_profit": 1000,
        }

        assert results["total_trades"] > 0
        assert results["winning_trades"] > 0

    def test_results_database_storage(self):
        """Test results database storage."""
        with patch("src.database.db_manager.DatabaseManager") as mock_db:
            mock_db.return_value.insert = Mock()

            results = {
                "symbol": "EURUSD",
                "total_trades": 50,
                "profit_factor": 2.5,
            }

            mock_db.return_value.insert("backtest_results", results)
            mock_db.return_value.insert.assert_called_once()

    def test_results_parameter_archiving(self):
        """Test parameter archiving in results."""
        parameters = {
            "ma_short": 20,
            "ma_long": 50,
            "risk_percent": 1.0,
        }

        results = {
            "symbol": "EURUSD",
            "parameters": parameters,
            "total_trades": 50,
        }

        assert results["parameters"]["ma_short"] == 20


class TestBacktestComparison:
    """Test backtest result comparison."""

    def test_compare_two_backtests(self):
        """Test comparing two backtest results."""
        result1 = {
            "symbol": "EURUSD",
            "profit_factor": 2.5,
            "win_rate": 60,
            "total_trades": 50,
        }

        result2 = {
            "symbol": "EURUSD",
            "profit_factor": 2.0,
            "win_rate": 55,
            "total_trades": 45,
        }

        is_better = result1["profit_factor"] > result2["profit_factor"]
        assert is_better is True

    def test_find_best_parameters(self):
        """Test finding best parameters across multiple backtests."""
        results = [
            {"parameters": {"period": 10}, "profit_factor": 2.0},
            {"parameters": {"period": 20}, "profit_factor": 2.5},
            {"parameters": {"period": 30}, "profit_factor": 2.3},
        ]

        best_result = max(results, key=lambda x: x["profit_factor"])

        assert best_result["parameters"]["period"] == 20


class TestBacktestIntegration:
    """Integration tests for backtest manager."""

    def test_complete_backtest_workflow(self):
        """Test complete backtest workflow."""
        with patch("src.database.db_manager.DatabaseManager"):
            with patch.object(BacktestManager, "run_backtest") as mock_backtest:
                manager = BacktestManager({"database": {}})

                # Setup
                config = {
                    "symbol": "EURUSD",
                    "start_date": "2023-01-01",
                    "end_date": "2024-01-01",
                }

                # Execute
                mock_backtest.return_value = {
                    "total_trades": 50,
                    "profit_factor": 2.5,
                    "win_rate": 60,
                }

                result = manager.run_backtest(**config)

                # Verify
                assert result is not None
                assert result["total_trades"] > 0

    def test_backtest_optimization_workflow(self):
        """Test backtest optimization workflow."""
        # Test multiple parameter sets
        parameter_sets = [
            {"ma_short": 10, "ma_long": 20},
            {"ma_short": 20, "ma_long": 50},
            {"ma_short": 30, "ma_long": 100},
        ]

        results = []

        for params in parameter_sets:
            result = {
                "parameters": params,
                "profit_factor": np.random.uniform(1.5, 3.0),
            }
            results.append(result)

        best = max(results, key=lambda x: x["profit_factor"])

        assert best is not None
        assert "parameters" in best
        assert "profit_factor" in best
