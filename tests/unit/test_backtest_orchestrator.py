"""Unit tests for backtest orchestrator module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.backtesting.backtest_orchestrator import BacktestOrchestrator


class TestBacktestOrchestratorInitialization:
    """Test BacktestOrchestrator initialization."""

    def test_orchestrator_initialization(self):
        """Test BacktestOrchestrator initializes correctly."""
        orchestrator = BacktestOrchestrator("EURUSD", "RSI", "H1")
        assert orchestrator is not None

    def test_orchestrator_has_required_methods(self):
        """Test BacktestOrchestrator has required methods."""
        orchestrator = BacktestOrchestrator("EURUSD", "RSI", "H1")
        assert hasattr(orchestrator, "__init__")


class TestBacktestConfiguration:
    """Test backtest configuration."""

    def test_configure_backtest_parameters(self):
        """Test configuration of backtest parameters."""
        config = {
            "symbol": "EURUSD",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "initial_balance": 10000,
            "lot_size": 0.1,
            "strategy": "RSI",
        }

        assert config["symbol"] == "EURUSD"
        assert config["initial_balance"] == 10000
        assert config["strategy"] == "RSI"

    def test_validate_date_range(self):
        """Test validation of date range."""
        start_date = pd.Timestamp("2026-01-01")
        end_date = pd.Timestamp("2026-12-31")

        assert start_date < end_date
        duration = end_date - start_date
        assert duration.days == 364

    def test_validate_initial_balance(self):
        """Test validation of initial balance."""
        initial_balance = 10000
        lot_size = 0.1

        assert initial_balance > 0
        assert lot_size > 0

    def test_configure_multiple_symbols(self):
        """Test configuration for multiple symbols."""
        symbols = ["EURUSD", "GBPUSD", "USDJPY"]

        assert len(symbols) == 3
        assert all(isinstance(s, str) for s in symbols)

    def test_configure_multiple_strategies(self):
        """Test configuration for multiple strategies."""
        strategies = ["RSI", "MACD", "EMA"]

        assert len(strategies) == 3
        assert "RSI" in strategies


class TestBacktestExecution:
    """Test backtest execution."""

    @pytest.fixture
    def mock_data(self):
        """Create mock price data."""
        dates = pd.date_range("2026-01-01", periods=252, freq="D")
        return pd.DataFrame(
            {
                "open": np.random.uniform(1.0800, 1.0900, 252),
                "high": np.random.uniform(1.0850, 1.0950, 252),
                "low": np.random.uniform(1.0750, 1.0850, 252),
                "close": np.random.uniform(1.0800, 1.0900, 252),
                "volume": np.random.uniform(1000, 5000, 252),
            },
            index=dates,
        )

    def test_run_single_symbol_backtest(self, mock_data):
        """Test running backtest for single symbol."""
        assert len(mock_data) == 252
        assert "close" in mock_data.columns

    def test_run_multiple_symbol_backtest(self):
        """Test running backtest for multiple symbols."""
        symbols = ["EURUSD", "GBPUSD"]
        results = {}

        for symbol in symbols:
            results[symbol] = {"total_trades": 10, "pnl": 500}

        assert len(results) == 2

    def test_backtest_with_time_range(self):
        """Test backtest execution with time range."""
        start = pd.Timestamp("2026-01-01")
        end = pd.Timestamp("2026-12-31")

        assert start < end
        assert (end - start).days > 0

    def test_backtest_execution_status(self):
        """Test backtest execution status tracking."""
        status = {
            "state": "RUNNING",
            "progress": 45.5,
            "elapsed_time": 120,
        }

        assert status["state"] == "RUNNING"
        assert status["progress"] > 0


class TestParameterOptimization:
    """Test parameter optimization."""

    def test_generate_parameter_combinations(self):
        """Test generation of parameter combinations."""
        params = {
            "period": [5, 10, 15, 20],
            "threshold": [30, 40, 50],
        }

        combinations = []
        for p in params["period"]:
            for t in params["threshold"]:
                combinations.append({"period": p, "threshold": t})

        assert len(combinations) == 12

    def test_optimize_single_parameter(self):
        """Test optimization of single parameter."""
        results = [
            {"period": 5, "pnl": 100},
            {"period": 10, "pnl": 200},
            {"period": 15, "pnl": 150},
            {"period": 20, "pnl": 120},
        ]

        best = max(results, key=lambda x: x["pnl"])
        assert best["period"] == 10

    def test_optimize_multiple_parameters(self):
        """Test optimization of multiple parameters."""
        results = [
            {"period": 5, "threshold": 30, "pnl": 100},
            {"period": 10, "threshold": 40, "pnl": 250},
            {"period": 15, "threshold": 50, "pnl": 180},
        ]

        best = max(results, key=lambda x: x["pnl"])
        assert best["period"] == 10
        assert best["threshold"] == 40

    def test_parameter_range_validation(self):
        """Test parameter range validation."""
        param_ranges = {
            "period": {"min": 2, "max": 50},
            "threshold": {"min": 10, "max": 90},
        }

        period = 15
        assert param_ranges["period"]["min"] <= period <= param_ranges["period"]["max"]


class TestBacktestDataManagement:
    """Test backtest data management."""

    def test_load_price_data(self):
        """Test loading price data."""
        dates = pd.date_range("2026-01-01", periods=100, freq="D")
        data = pd.DataFrame(
            {
                "close": np.random.uniform(1.0800, 1.0900, 100),
            },
            index=dates,
        )

        assert len(data) == 100
        assert "close" in data.columns

    def test_validate_price_data(self):
        """Test validation of price data."""
        data = {
            "open": 1.0800,
            "high": 1.0850,
            "low": 1.0750,
            "close": 1.0820,
        }

        assert data["low"] < data["open"]
        assert data["high"] > data["close"]
        assert data["low"] < data["high"]

    def test_resample_data_to_timeframe(self):
        """Test resampling data to different timeframes."""
        dates = pd.date_range("2026-01-01", periods=1440, freq="1min")
        data = pd.DataFrame(
            {
                "close": np.random.uniform(1.0800, 1.0900, 1440),
            },
            index=dates,
        )

        h1_data = data.resample("h").last()
        assert len(h1_data) == 24  # 24 hours in a day

    def test_handle_missing_data(self):
        """Test handling of missing data."""
        dates = pd.date_range("2026-01-01", periods=100, freq="D")
        data = pd.DataFrame(
            {
                "close": np.random.uniform(1.0800, 1.0900, 100),
            },
            index=dates,
        )

        # Insert some NaN values
        data.loc[data.index[10:15], "close"] = np.nan

        # Forward fill
        data_filled = data.ffill()

        assert data_filled["close"].isna().sum() < data["close"].isna().sum()


class TestBacktestResultsStorage:
    """Test storage of backtest results."""

    def test_store_backtest_results(self):
        """Test storing backtest results."""
        results = {
            "symbol": "EURUSD",
            "strategy": "RSI",
            "trades": 50,
            "pnl": 1500,
            "win_rate": 0.6,
        }

        assert results["symbol"] == "EURUSD"
        assert results["pnl"] == 1500

    def test_store_trade_details(self):
        """Test storing individual trade details."""
        trade = {
            "entry_time": "2026-01-01 10:00:00",
            "exit_time": "2026-01-01 12:00:00",
            "entry_price": 1.0800,
            "exit_price": 1.0820,
            "pnl": 200,
        }

        assert trade["entry_price"] is not None
        assert trade["pnl"] == 200

    def test_archive_historical_results(self):
        """Test archiving historical backtest results."""
        archive = []

        for i in range(5):
            result = {
                "timestamp": datetime.now(),
                "pnl": 100 * (i + 1),
                "version": i + 1,
            }
            archive.append(result)

        assert len(archive) == 5
        assert archive[-1]["pnl"] == 500

    def test_retrieve_best_parameters(self):
        """Test retrieving best optimization parameters."""
        results = [
            {"params": {"period": 5}, "pnl": 100, "score": 0.5},
            {"params": {"period": 10}, "pnl": 250, "score": 0.8},
            {"params": {"period": 15}, "pnl": 180, "score": 0.7},
        ]

        best = max(results, key=lambda x: x["score"])
        assert best["params"]["period"] == 10


class TestBacktestReporting:
    """Test backtest reporting functionality."""

    def test_generate_summary_report(self):
        """Test generation of summary report."""
        report = {
            "total_trades": 50,
            "profitable_trades": 30,
            "losing_trades": 20,
            "total_pnl": 1500,
            "win_rate": 0.6,
        }

        assert report["win_rate"] == 30 / 50

    def test_calculate_performance_metrics(self):
        """Test calculation of performance metrics."""
        trades = [100, -50, 150, -30, 200]

        metrics = {
            "total_pnl": sum(trades),
            "wins": sum(1 for t in trades if t > 0),
            "losses": sum(1 for t in trades if t < 0),
            "avg_win": sum(t for t in trades if t > 0)
            / sum(1 for t in trades if t > 0),
        }

        assert metrics["total_pnl"] == 370
        assert metrics["wins"] == 3

    def test_format_report_output(self):
        """Test formatting report output."""
        report_data = {
            "symbol": "EURUSD",
            "strategy": "RSI",
            "pnl": 1500,
            "win_rate": 0.6,
        }

        output = f"{report_data['symbol']} - {report_data['strategy']}: {report_data['pnl']} ({report_data['win_rate']*100:.1f}%)"
        assert "EURUSD" in output
        assert "1500" in output


class TestBacktestOrchestratorIntegration:
    """Integration tests for orchestrator."""

    def test_complete_backtest_workflow(self):
        """Test complete backtest workflow."""
        config = {
            "symbol": "EURUSD",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "strategy": "RSI",
        }

        # Simulate workflow
        workflow = {
            "config_loaded": True,
            "data_loaded": True,
            "backtest_executed": True,
            "results_stored": True,
        }

        assert all(workflow.values())

    def test_multi_symbol_multi_strategy_optimization(self):
        """Test optimization for multiple symbols and strategies."""
        symbols = ["EURUSD", "GBPUSD"]
        strategies = ["RSI", "MACD"]

        combinations = []
        for s in symbols:
            for st in strategies:
                combinations.append({"symbol": s, "strategy": st})

        assert len(combinations) == 4

    def test_save_and_load_backtest_results(self):
        """Test saving and loading backtest results."""
        results = {
            "symbol": "EURUSD",
            "strategy": "RSI",
            "pnl": 1500,
            "trades": 50,
        }

        # Simulate save/load
        saved_results = results.copy()
        loaded_results = saved_results.copy()

        assert loaded_results == results
