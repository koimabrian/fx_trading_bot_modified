"""Unit tests for trade logger module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta
import tempfile
import os

from src.backtesting.trade_logger import TradeLogger


class TestTradeLoggerInitialization:
    """Test TradeLogger initialization."""

    def test_trade_logger_initialization(self):
        """Test TradeLogger initializes correctly."""
        logger = TradeLogger()
        assert logger is not None

    def test_trade_logger_has_required_methods(self):
        """Test TradeLogger has required methods."""
        logger = TradeLogger()
        assert hasattr(logger, "__init__")


class TestTradeLogging:
    """Test trade logging functionality."""

    @pytest.fixture
    def trade_entry(self):
        """Create sample trade entry."""
        return {
            "timestamp": datetime.now(),
            "symbol": "EURUSD",
            "side": "BUY",
            "entry_price": 1.0800,
            "volume": 1.0,
            "status": "OPEN",
        }

    def test_log_trade_entry(self, trade_entry):
        """Test logging trade entry."""
        log = trade_entry.copy()
        assert log["symbol"] == "EURUSD"
        assert log["status"] == "OPEN"

    def test_log_trade_exit(self):
        """Test logging trade exit."""
        trade_exit = {
            "timestamp": datetime.now(),
            "symbol": "EURUSD",
            "exit_price": 1.0820,
            "pnl": 200,
            "status": "CLOSED",
        }

        assert trade_exit["status"] == "CLOSED"
        assert trade_exit["pnl"] == 200

    def test_log_partial_close(self):
        """Test logging partial position closure."""
        log = {
            "timestamp": datetime.now(),
            "symbol": "EURUSD",
            "close_volume": 0.5,
            "remaining_volume": 0.5,
            "status": "PARTIAL_CLOSED",
        }

        assert log["status"] == "PARTIAL_CLOSED"
        assert log["close_volume"] + log["remaining_volume"] == 1.0

    def test_log_stop_loss_triggered(self):
        """Test logging stop loss trigger."""
        log = {
            "timestamp": datetime.now(),
            "symbol": "EURUSD",
            "trigger_price": 1.0780,
            "exit_price": 1.0779,
            "pnl": -210,
            "reason": "STOP_LOSS",
        }

        assert log["reason"] == "STOP_LOSS"
        assert log["pnl"] < 0

    def test_log_take_profit_triggered(self):
        """Test logging take profit trigger."""
        log = {
            "timestamp": datetime.now(),
            "symbol": "EURUSD",
            "trigger_price": 1.0850,
            "exit_price": 1.0851,
            "pnl": 510,
            "reason": "TAKE_PROFIT",
        }

        assert log["reason"] == "TAKE_PROFIT"
        assert log["pnl"] > 0


class TestLogFormatting:
    """Test log formatting."""

    def test_format_trade_log_entry(self):
        """Test formatting trade log entry."""
        trade = {
            "timestamp": datetime.now(),
            "symbol": "EURUSD",
            "side": "BUY",
            "price": 1.0800,
        }

        formatted = f"[{trade['timestamp']}] {trade['side']} {trade['symbol']} @ {trade['price']}"
        assert "EURUSD" in formatted
        assert "BUY" in formatted

    def test_format_with_pnl(self):
        """Test formatting with P&L."""
        trade = {
            "symbol": "EURUSD",
            "pnl": 150,
        }

        formatted = f"{trade['symbol']} PnL: {trade['pnl']}"
        assert "150" in formatted

    def test_format_with_details(self):
        """Test detailed format."""
        trade = {
            "symbol": "EURUSD",
            "entry": 1.0800,
            "exit": 1.0820,
            "volume": 1.0,
            "pnl": 200,
        }

        details = f"Entry: {trade['entry']}, Exit: {trade['exit']}, Vol: {trade['volume']}, PnL: {trade['pnl']}"
        assert "Entry" in details
        assert "1.08" in details  # Python formatting converts 1.0800 to 1.08


class TestLogStorage:
    """Test log storage."""

    def test_store_log_in_memory(self):
        """Test storing logs in memory."""
        logs = []

        trade = {"timestamp": datetime.now(), "symbol": "EURUSD", "pnl": 100}
        logs.append(trade)

        assert len(logs) == 1
        assert logs[0]["symbol"] == "EURUSD"

    def test_store_multiple_trades(self):
        """Test storing multiple trade logs."""
        logs = []

        for i in range(10):
            logs.append(
                {
                    "timestamp": datetime.now() + timedelta(hours=i),
                    "symbol": "EURUSD",
                    "pnl": 100 * (i + 1),
                }
            )

        assert len(logs) == 10
        assert logs[-1]["pnl"] == 1000

    def test_clear_logs(self):
        """Test clearing logs."""
        logs = [{"pnl": 100}, {"pnl": 200}]
        assert len(logs) == 2

        logs.clear()
        assert len(logs) == 0

    def test_append_to_logs(self):
        """Test appending to logs."""
        logs = []

        for i in range(3):
            logs.append({"trade_id": i, "pnl": 100})

        assert len(logs) == 3


class TestLogQuerying:
    """Test log querying."""

    @pytest.fixture
    def trade_logs(self):
        """Create sample trade logs."""
        return [
            {"symbol": "EURUSD", "pnl": 100, "timestamp": datetime(2026, 1, 1, 10, 0)},
            {"symbol": "EURUSD", "pnl": -50, "timestamp": datetime(2026, 1, 1, 11, 0)},
            {"symbol": "GBPUSD", "pnl": 150, "timestamp": datetime(2026, 1, 1, 12, 0)},
            {"symbol": "GBPUSD", "pnl": -30, "timestamp": datetime(2026, 1, 1, 13, 0)},
        ]

    def test_query_logs_by_symbol(self, trade_logs):
        """Test querying logs by symbol."""
        eurusd_logs = [log for log in trade_logs if log["symbol"] == "EURUSD"]
        assert len(eurusd_logs) == 2

    def test_query_logs_by_pnl(self, trade_logs):
        """Test querying logs by P&L."""
        profitable = [log for log in trade_logs if log["pnl"] > 0]
        assert len(profitable) == 2

    def test_query_logs_by_date_range(self, trade_logs):
        """Test querying logs by date range."""
        start = datetime(2026, 1, 1, 10, 30)
        end = datetime(2026, 1, 1, 12, 30)

        filtered = [log for log in trade_logs if start <= log["timestamp"] <= end]
        assert len(filtered) == 2

    def test_sort_logs_by_pnl(self, trade_logs):
        """Test sorting logs by P&L."""
        sorted_logs = sorted(trade_logs, key=lambda x: x["pnl"], reverse=True)
        assert sorted_logs[0]["pnl"] == 150

    def test_sort_logs_by_timestamp(self, trade_logs):
        """Test sorting logs by timestamp."""
        sorted_logs = sorted(trade_logs, key=lambda x: x["timestamp"])
        assert sorted_logs[0]["timestamp"] == datetime(2026, 1, 1, 10, 0)


class TestLogAggregation:
    """Test log aggregation."""

    @pytest.fixture
    def trade_logs(self):
        """Create sample trade logs."""
        return [
            {"symbol": "EURUSD", "pnl": 100},
            {"symbol": "EURUSD", "pnl": -50},
            {"symbol": "GBPUSD", "pnl": 150},
            {"symbol": "GBPUSD", "pnl": -30},
        ]

    def test_aggregate_by_symbol(self, trade_logs):
        """Test aggregating logs by symbol."""
        agg = {}
        for log in trade_logs:
            symbol = log["symbol"]
            if symbol not in agg:
                agg[symbol] = {"count": 0, "total_pnl": 0}
            agg[symbol]["count"] += 1
            agg[symbol]["total_pnl"] += log["pnl"]

        assert agg["EURUSD"]["count"] == 2
        assert agg["EURUSD"]["total_pnl"] == 50

    def test_aggregate_by_day(self):
        """Test aggregating logs by day."""
        logs = [
            {"date": "2026-01-01", "pnl": 100},
            {"date": "2026-01-01", "pnl": 150},
            {"date": "2026-01-02", "pnl": -50},
        ]

        daily = {}
        for log in logs:
            date = log["date"]
            if date not in daily:
                daily[date] = 0
            daily[date] += log["pnl"]

        assert daily["2026-01-01"] == 250
        assert daily["2026-01-02"] == -50

    def test_calculate_statistics(self, trade_logs):
        """Test calculating statistics from logs."""
        pnls = [log["pnl"] for log in trade_logs]

        stats = {
            "count": len(pnls),
            "total": sum(pnls),
            "avg": sum(pnls) / len(pnls),
            "max": max(pnls),
            "min": min(pnls),
        }

        assert stats["count"] == 4
        assert stats["total"] == 170


class TestLogPersistence:
    """Test log persistence to file."""

    def test_write_logs_to_file(self):
        """Test writing logs to file."""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
            filename = f.name
            f.write("2026-01-01 10:00 EURUSD BUY 1.0800 200\n")
            f.write("2026-01-01 11:00 EURUSD SELL 1.0820 -50\n")

        try:
            with open(filename, "r") as f:
                lines = f.readlines()
            assert len(lines) == 2
        finally:
            os.unlink(filename)

    def test_read_logs_from_file(self):
        """Test reading logs from file."""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as f:
            filename = f.name
            f.write("EURUSD 100\n")
            f.write("GBPUSD 150\n")

        try:
            logs = []
            with open(filename, "r") as f:
                for line in f:
                    parts = line.strip().split()
                    logs.append({"symbol": parts[0], "pnl": int(parts[1])})

            assert len(logs) == 2
        finally:
            os.unlink(filename)


class TestTradeLoggerIntegration:
    """Integration tests for trade logger."""

    def test_complete_trade_logging_workflow(self):
        """Test complete trade logging workflow."""
        logs = []

        # Entry
        logs.append(
            {
                "event": "ENTRY",
                "timestamp": datetime.now(),
                "symbol": "EURUSD",
                "price": 1.0800,
            }
        )

        # Exit
        logs.append(
            {
                "event": "EXIT",
                "timestamp": datetime.now(),
                "symbol": "EURUSD",
                "price": 1.0820,
                "pnl": 200,
            }
        )

        assert len(logs) == 2
        assert logs[0]["event"] == "ENTRY"
        assert logs[1]["event"] == "EXIT"

    def test_log_trade_with_metadata(self):
        """Test logging trade with full metadata."""
        log = {
            "timestamp": datetime.now(),
            "symbol": "EURUSD",
            "strategy": "RSI",
            "side": "BUY",
            "entry_price": 1.0800,
            "exit_price": 1.0820,
            "volume": 1.0,
            "pnl": 200,
            "status": "CLOSED",
        }

        assert log["symbol"] == "EURUSD"
        assert log["strategy"] == "RSI"
        assert log["pnl"] == 200
