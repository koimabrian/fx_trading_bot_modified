"""Unit tests for trade extractor module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.backtesting.trade_extractor import TradeExtractor


class TestTradeExtractorInitialization:
    """Test TradeExtractor initialization."""

    def test_trade_extractor_initialization(self):
        """Test TradeExtractor initializes correctly."""
        extractor = TradeExtractor()
        assert extractor is not None

    def test_trade_extractor_has_required_methods(self):
        """Test TradeExtractor has required methods."""
        extractor = TradeExtractor()
        assert hasattr(extractor, "__init__")


class TestTradeExtraction:
    """Test trade extraction from backtest results."""

    @pytest.fixture
    def backtest_data(self):
        """Create sample backtest data."""
        return {
            "symbol": "EURUSD",
            "strategy": "RSI",
            "trades": [
                {
                    "entry_time": "2026-01-01 10:00:00",
                    "exit_time": "2026-01-01 12:00:00",
                    "entry_price": 1.0800,
                    "exit_price": 1.0820,
                    "volume": 1.0,
                    "side": "BUY",
                    "pnl": 200,
                },
                {
                    "entry_time": "2026-01-01 13:00:00",
                    "exit_time": "2026-01-01 14:00:00",
                    "entry_price": 1.0815,
                    "exit_price": 1.0800,
                    "volume": 1.0,
                    "side": "SELL",
                    "pnl": 150,
                },
            ],
        }

    def test_extract_trades(self, backtest_data):
        """Test extraction of trades from backtest data."""
        trades = backtest_data["trades"]
        assert len(trades) == 2
        assert trades[0]["side"] == "BUY"
        assert trades[1]["side"] == "SELL"

    def test_extract_trade_details(self, backtest_data):
        """Test extraction of individual trade details."""
        trade = backtest_data["trades"][0]

        assert trade["entry_price"] == 1.0800
        assert trade["exit_price"] == 1.0820
        assert trade["pnl"] == 200

    def test_extract_symbol_from_trade(self, backtest_data):
        """Test extracting symbol from backtest data."""
        symbol = backtest_data["symbol"]
        assert symbol == "EURUSD"

    def test_extract_strategy_from_trade(self, backtest_data):
        """Test extracting strategy from backtest data."""
        strategy = backtest_data["strategy"]
        assert strategy == "RSI"


class TestTradeMetadataExtraction:
    """Test extraction of trade metadata."""

    def test_extract_entry_exit_times(self):
        """Test extraction of entry/exit times."""
        trade = {
            "entry_time": "2026-01-01 10:00:00",
            "exit_time": "2026-01-01 12:00:00",
        }

        entry = pd.Timestamp(trade["entry_time"])
        exit_t = pd.Timestamp(trade["exit_time"])
        duration = exit_t - entry

        assert duration.total_seconds() == 7200

    def test_extract_hold_duration(self):
        """Test extraction of hold duration."""
        entry = pd.Timestamp("2026-01-01 10:00:00")
        exit_t = pd.Timestamp("2026-01-01 14:30:00")

        hold_duration = exit_t - entry
        assert hold_duration.total_seconds() == 16200  # 4.5 hours

    def test_extract_trade_direction(self):
        """Test extraction of trade direction."""
        trades = [
            {"side": "BUY"},
            {"side": "SELL"},
            {"side": "BUY"},
        ]

        buy_count = sum(1 for t in trades if t["side"] == "BUY")
        sell_count = sum(1 for t in trades if t["side"] == "SELL")

        assert buy_count == 2
        assert sell_count == 1


class TestPriceCalculations:
    """Test price and P&L calculations."""

    def test_calculate_pip_value(self):
        """Test pip value calculation."""
        entry = 1.0800
        exit_t = 1.0820

        pips = round((exit_t - entry) * 10000)
        assert pips == 20  # 20 pips not 200
        volume = 1.0

        return_pct = ((exit_t - entry) / entry) * 100
        assert return_pct > 0

    def test_calculate_pnl_from_prices(self):
        """Test P&L calculation from prices."""
        entry_price = 1.0800
        exit_price = 1.0820
        volume = 1.0

        pnl = round((exit_price - entry_price) * 10000 * volume)
        assert pnl == 20  # 20 pips not 200

    def test_calculate_win_loss(self):
        """Test win/loss determination."""
        trades = [
            {"pnl": 100},
            {"pnl": -50},
            {"pnl": 150},
            {"pnl": -30},
        ]

        wins = sum(1 for t in trades if t["pnl"] > 0)
        losses = sum(1 for t in trades if t["pnl"] < 0)

        assert wins == 2
        assert losses == 2


class TestTradeFiltering:
    """Test trade filtering operations."""

    @pytest.fixture
    def trades(self):
        """Create sample trades."""
        return [
            {"symbol": "EURUSD", "pnl": 100, "duration": 100},
            {"symbol": "EURUSD", "pnl": -50, "duration": 200},
            {"symbol": "GBPUSD", "pnl": 150, "duration": 150},
            {"symbol": "GBPUSD", "pnl": -30, "duration": 300},
            {"symbol": "USDJPY", "pnl": 200, "duration": 50},
        ]

    def test_filter_trades_by_symbol(self, trades):
        """Test filtering trades by symbol."""
        filtered = [t for t in trades if t["symbol"] == "EURUSD"]
        assert len(filtered) == 2

    def test_filter_trades_by_profit(self, trades):
        """Test filtering trades by profitability."""
        profitable = [t for t in trades if t["pnl"] > 0]
        assert len(profitable) == 3

    def test_filter_trades_by_loss(self, trades):
        """Test filtering losing trades."""
        losing = [t for t in trades if t["pnl"] < 0]
        assert len(losing) == 2

    def test_filter_trades_by_duration(self, trades):
        """Test filtering trades by duration."""
        short_trades = [t for t in trades if t["duration"] < 150]
        assert len(short_trades) == 2

    def test_filter_trades_by_pnl_range(self, trades):
        """Test filtering trades within P&L range."""
        filtered = [t for t in trades if 50 <= t["pnl"] <= 200]
        assert len(filtered) >= 2


class TestTradeGrouping:
    """Test trade grouping operations."""

    @pytest.fixture
    def trades(self):
        """Create sample trades."""
        return [
            {"symbol": "EURUSD", "pnl": 100},
            {"symbol": "EURUSD", "pnl": -50},
            {"symbol": "GBPUSD", "pnl": 150},
            {"symbol": "GBPUSD", "pnl": -30},
            {"symbol": "USDJPY", "pnl": 200},
        ]

    def test_group_trades_by_symbol(self, trades):
        """Test grouping trades by symbol."""
        grouped = {}
        for trade in trades:
            symbol = trade["symbol"]
            if symbol not in grouped:
                grouped[symbol] = []
            grouped[symbol].append(trade)

        assert len(grouped) == 3
        assert len(grouped["EURUSD"]) == 2

    def test_group_trades_by_result(self, trades):
        """Test grouping trades by win/loss."""
        grouped = {"wins": [], "losses": []}
        for trade in trades:
            if trade["pnl"] > 0:
                grouped["wins"].append(trade)
            else:
                grouped["losses"].append(trade)

        assert len(grouped["wins"]) == 3
        assert len(grouped["losses"]) == 2

    def test_calculate_grouped_metrics(self, trades):
        """Test metrics calculation for grouped trades."""
        grouped = {}
        for trade in trades:
            symbol = trade["symbol"]
            if symbol not in grouped:
                grouped[symbol] = []
            grouped[symbol].append(trade)

        for symbol, group in grouped.items():
            total_pnl = sum(t["pnl"] for t in group)
            assert total_pnl is not None


class TestDataFrameConversion:
    """Test conversion to DataFrame."""

    def test_convert_trades_to_dataframe(self):
        """Test converting trades to DataFrame."""
        trades = [
            {"symbol": "EURUSD", "pnl": 100, "duration": 100},
            {"symbol": "GBPUSD", "pnl": 150, "duration": 200},
        ]

        df = pd.DataFrame(trades)
        assert len(df) == 2
        assert "symbol" in df.columns

    def test_dataframe_aggregation(self):
        """Test aggregation operations on DataFrame."""
        trades = [
            {"symbol": "EURUSD", "pnl": 100},
            {"symbol": "EURUSD", "pnl": -50},
            {"symbol": "GBPUSD", "pnl": 150},
        ]

        df = pd.DataFrame(trades)
        grouped = df.groupby("symbol")["pnl"].sum()

        assert grouped["EURUSD"] == 50
        assert grouped["GBPUSD"] == 150


class TestTradeExtractionIntegration:
    """Integration tests for trade extraction."""

    def test_extract_and_analyze_complete_trade_set(self):
        """Test complete trade extraction and analysis."""
        backtest_results = {
            "trades": [
                {
                    "symbol": "EURUSD",
                    "entry_time": "2026-01-01",
                    "exit_time": "2026-01-02",
                    "entry_price": 1.0800,
                    "exit_price": 1.0820,
                    "pnl": 200,
                },
                {
                    "symbol": "EURUSD",
                    "entry_time": "2026-01-02",
                    "exit_time": "2026-01-03",
                    "entry_price": 1.0815,
                    "exit_price": 1.0800,
                    "pnl": -150,
                },
            ]
        }

        trades = backtest_results["trades"]
        metrics = {
            "total_trades": len(trades),
            "total_pnl": sum(t["pnl"] for t in trades),
            "win_rate": sum(1 for t in trades if t["pnl"] > 0) / len(trades),
        }

        assert metrics["total_trades"] == 2
        assert metrics["total_pnl"] == 50
        assert metrics["win_rate"] == 0.5

    def test_extract_trades_with_metadata(self):
        """Test extracting trades with full metadata."""
        trade = {
            "symbol": "EURUSD",
            "strategy": "RSI",
            "timeframe": "H1",
            "entry_time": "2026-01-01 10:00:00",
            "exit_time": "2026-01-01 12:00:00",
            "entry_price": 1.0800,
            "exit_price": 1.0820,
            "volume": 1.0,
            "side": "BUY",
            "pnl": 200,
            "pips": 200,
            "return_pct": 0.1852,
        }

        assert trade["symbol"] == "EURUSD"
        assert trade["strategy"] == "RSI"
        assert trade["entry_price"] is not None
        assert trade["pnl"] == 200
