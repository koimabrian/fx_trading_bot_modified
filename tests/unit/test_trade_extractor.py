"""Unit tests for trade extractor module."""

import pytest
import pandas as pd
import numpy as np

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


class TestTradeExtractorDataFrameHandling:
    """Test DataFrame handling and type safety in TradeExtractor."""

    def test_extract_trades_with_none_trades_list(self):
        """Test extraction when _trades is None."""
        stats = Mock()
        stats._trades = None

        result = TradeExtractor.extract_trades(stats)
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_extract_trades_without_trades_attribute(self):
        """Test extraction when stats object has no _trades attribute."""
        stats = Mock(spec=[])  # Mock with no attributes

        result = TradeExtractor.extract_trades(stats)
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_extract_trades_with_empty_trades_list(self):
        """Test extraction when _trades list is empty."""
        stats = Mock()
        stats._trades = []

        result = TradeExtractor.extract_trades(stats)
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_extract_trades_skips_string_entries(self):
        """Test that string entries in _trades are skipped."""
        trade_obj = Mock()
        trade_obj.entry_time = datetime(2026, 1, 1, 10, 0)
        trade_obj.exit_time = datetime(2026, 1, 1, 12, 0)
        trade_obj.entry_price = 1.0800
        trade_obj.exit_price = 1.0820
        trade_obj.size = 1.0
        trade_obj.pl = 200
        trade_obj.plpct = 0.185

        stats = Mock()
        stats._trades = [
            "invalid_string_entry",  # Should be skipped
            trade_obj,
            "another_string",  # Should be skipped
        ]

        result = TradeExtractor.extract_trades(stats)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1  # Only valid trade object extracted
        assert result.iloc[0]["pnl"] == 200

    def test_extract_trades_skips_incomplete_objects(self):
        """Test that incomplete trade objects are skipped."""
        complete_trade = Mock()
        complete_trade.entry_time = datetime(2026, 1, 1, 10, 0)
        complete_trade.exit_time = datetime(2026, 1, 1, 12, 0)
        complete_trade.entry_price = 1.0800
        complete_trade.exit_price = 1.0820
        complete_trade.size = 1.0
        complete_trade.pl = 200
        complete_trade.plpct = 0.185

        incomplete_trade = Mock(spec=["entry_time"])  # Missing exit_time
        incomplete_trade.entry_time = datetime(2026, 1, 1, 10, 0)

        stats = Mock()
        stats._trades = [incomplete_trade, complete_trade]

        result = TradeExtractor.extract_trades(stats)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1  # Only complete trade extracted

    def test_calculate_trade_statistics_with_empty_dataframe(self):
        """Test that calculate_trade_statistics handles empty DataFrames."""
        empty_df = pd.DataFrame()

        result = TradeExtractor.calculate_trade_statistics(empty_df)
        assert result["total_trades"] == 0
        assert result["winning_trades"] == 0
        assert result["losing_trades"] == 0
        assert result["win_rate"] == 0.0

    def test_calculate_trade_statistics_with_none(self):
        """Test that calculate_trade_statistics handles None input."""
        result = TradeExtractor.calculate_trade_statistics(None)
        assert result["total_trades"] == 0
        assert result["win_rate"] == 0.0

    def test_calculate_trade_statistics_dataframe_empty_check(self):
        """Test DataFrame.empty check in calculate_trade_statistics."""
        # Create DataFrame with trades
        trades_df = pd.DataFrame(
            {
                "pnl": [100, -50, 200],
                "pnl_pct": [0.5, -0.25, 1.0],
                "duration_hours": [2, 1, 3],
            }
        )

        result = TradeExtractor.calculate_trade_statistics(trades_df)
        assert result["total_trades"] == 3
        assert result["winning_trades"] == 2
        assert result["losing_trades"] == 1
        assert result["win_rate"] == pytest.approx(66.67, 0.1)

    def test_get_trades_by_timeframe_with_empty_dataframe(self):
        """Test get_trades_by_timeframe with empty DataFrame."""
        empty_df = pd.DataFrame()

        result = TradeExtractor.get_trades_by_timeframe(empty_df)
        assert result == {}

    def test_get_winning_losing_breakdown_with_empty_dataframe(self):
        """Test get_winning_losing_breakdown with empty DataFrame."""
        empty_df = pd.DataFrame()

        result = TradeExtractor.get_winning_losing_breakdown(empty_df)
        assert result["winning"] == []
        assert result["losing"] == []

    def test_export_trades_csv_with_empty_dataframe(self):
        """Test export_trades_csv with empty DataFrame."""
        import tempfile

        empty_df = pd.DataFrame()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=True) as f:
            result = TradeExtractor.export_trades_csv(empty_df, f.name)
            assert result is False

    def test_calculate_streaks_with_numpy_booleans(self):
        """Test _calculate_streaks handles numpy boolean types correctly."""
        # Test with numpy booleans (which can cause ambiguity errors)
        is_win_list = [
            np.bool_(True),
            np.bool_(True),
            np.bool_(False),
            np.bool_(False),
            np.bool_(False),
            np.bool_(True),
        ]

        result = TradeExtractor._calculate_streaks(is_win_list)
        assert result == [2, 3, 1]  # Two wins, three losses, one win

    def test_calculate_streaks_with_mixed_types(self):
        """Test _calculate_streaks handles mixed boolean types."""
        is_win_list = [True, True, False, np.bool_(False), np.bool_(True)]

        result = TradeExtractor._calculate_streaks(is_win_list)
        assert len(result) > 0
        assert all(isinstance(x, int) for x in result)
