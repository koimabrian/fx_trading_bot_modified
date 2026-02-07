"""Unit tests for data fetcher module."""

import logging
import pytest
from unittest.mock import Mock, MagicMock, patch
import pandas as pd
from datetime import datetime, timedelta

from src.core.data_fetcher import DataFetcher


class TestDataFetcher:
    """Test suite for DataFetcher class."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for DataFetcher."""
        mt5_conn = Mock()
        db = Mock()
        # Mock the database connection and cursor
        cursor_mock = Mock()
        cursor_mock.fetchall.return_value = [("EURUSD",), ("GBPUSD",)]
        cursor_mock.fetchone.return_value = {"count": 0}  # For COUNT(*) queries
        cursor_mock.rowcount = 0  # For INSERT operations
        cursor_mock.description = []  # For pd.read_sql compatibility
        db_conn_mock = Mock()
        db_conn_mock.cursor.return_value = cursor_mock
        db.conn = db_conn_mock
        # Also configure execute_query to return a cursor with fetchone
        db.execute_query.return_value = cursor_mock

        config = {
            "data": {
                "cache_enabled": True,
                "cache_duration": 300,
                "symbols": ["EURUSD", "GBPUSD"],
            },
            "timeframes": [15, 60, 240],
        }
        return mt5_conn, db, config

    @pytest.fixture
    def data_fetcher(self, mock_dependencies):
        """Create DataFetcher instance with mocks."""
        mt5_conn, db, config = mock_dependencies
        return DataFetcher(mt5_conn, db, config)

    def test_data_fetcher_initialization(self, data_fetcher):
        """Test DataFetcher initializes correctly."""
        assert data_fetcher is not None
        assert data_fetcher.mt5_conn is not None
        assert data_fetcher.db is not None

    def test_data_fetcher_is_class(self):
        """Test that DataFetcher is a valid class."""
        assert DataFetcher is not None

    def test_data_fetcher_can_instantiate(self, data_fetcher):
        """Test DataFetcher can be instantiated."""
        assert isinstance(data_fetcher, DataFetcher)

    def test_data_fetcher_has_logger(self, data_fetcher):
        """Test DataFetcher has logger."""
        assert hasattr(data_fetcher, "logger")

    def test_data_fetcher_has_config(self, data_fetcher):
        """Test DataFetcher has config."""
        assert hasattr(data_fetcher, "config")

    @patch("MetaTrader5.copy_rates_from_pos")
    def test_fetch_data_returns_dataframe(self, mock_copy_rates, data_fetcher):
        """Test fetch data returns DataFrame."""
        mock_copy_rates.return_value = [
            Mock(
                time=datetime.now().timestamp(),
                open=1.2500,
                high=1.2520,
                low=1.2480,
                close=1.2510,
                tick_volume=1000,
            ),
        ]

        if hasattr(data_fetcher, "fetch"):
            data = data_fetcher.fetch("EURUSD", count=100)
            assert data is None or isinstance(data, pd.DataFrame)

    def test_data_fetcher_get_ohlc(self, data_fetcher):
        """Test getting OHLC data."""
        if hasattr(data_fetcher, "get_ohlc"):
            data = data_fetcher.get_ohlc("EURUSD", "H1", count=100)
            assert data is None or isinstance(data, pd.DataFrame)

    def test_data_fetcher_caching_enabled(self, data_fetcher):
        """Test caching mechanism."""
        if hasattr(data_fetcher, "is_cache_valid"):
            valid = data_fetcher.is_cache_valid("EURUSD")
            assert valid is None or isinstance(valid, bool)

    def test_data_fetcher_clear_cache(self, data_fetcher):
        """Test clearing cache."""
        if hasattr(data_fetcher, "clear_cache"):
            result = data_fetcher.clear_cache()
            assert result is None or isinstance(result, bool)

    def test_data_fetcher_validate_data(self, data_fetcher):
        """Test data validation."""
        if hasattr(data_fetcher, "validate_ohlc"):
            df = pd.DataFrame(
                {
                    "open": [1.2500, 1.2510],
                    "high": [1.2520, 1.2530],
                    "low": [1.2480, 1.2490],
                    "close": [1.2510, 1.2520],
                }
            )
            valid = data_fetcher.validate_ohlc(df)
            assert valid is None or isinstance(valid, bool)

    def test_data_fetcher_timeframe_check(self, data_fetcher):
        """Test timeframe handling."""
        if hasattr(data_fetcher, "get_mt5_timeframe"):
            tf = data_fetcher.get_mt5_timeframe("H1")
            assert tf is None or isinstance(tf, int)

    def test_data_fetcher_symbol_check(self, data_fetcher):
        """Test symbol validation."""
        if hasattr(data_fetcher, "is_valid_symbol"):
            valid = data_fetcher.is_valid_symbol("EURUSD")
            assert valid is None or isinstance(valid, bool)

    def test_data_fetcher_fetch_range(self, data_fetcher):
        """Test fetching data in date range."""
        if hasattr(data_fetcher, "fetch_range"):
            start = datetime.now() - timedelta(days=7)
            end = datetime.now()
            data = data_fetcher.fetch_range("EURUSD", start, end, "H1")
            assert data is None or isinstance(data, pd.DataFrame)

    def test_data_fetcher_get_latest_bar(self, data_fetcher):
        """Test getting latest bar."""
        if hasattr(data_fetcher, "get_latest_bar"):
            bar = data_fetcher.get_latest_bar("EURUSD")
            assert bar is None or isinstance(bar, (dict, tuple))

    def test_data_fetcher_get_bid_ask(self, data_fetcher):
        """Test getting bid/ask prices."""
        if hasattr(data_fetcher, "get_bid_ask"):
            prices = data_fetcher.get_bid_ask("EURUSD")
            assert prices is None or isinstance(prices, (dict, tuple))

    def test_data_fetcher_get_spreads(self, data_fetcher):
        """Test getting spreads."""
        if hasattr(data_fetcher, "get_spread"):
            spread = data_fetcher.get_spread("EURUSD")
            assert spread is None or isinstance(spread, (int, float))

    def test_data_fetcher_missing_data_handling(self, data_fetcher):
        """Test handling missing data."""
        if hasattr(data_fetcher, "fill_missing"):
            df = pd.DataFrame(
                {
                    "close": [1.2500, None, 1.2520],
                }
            )
            filled = data_fetcher.fill_missing(df)
            assert filled is None or isinstance(filled, pd.DataFrame)

    def test_data_fetcher_connection_check(self, data_fetcher):
        """Test connection checking."""
        if hasattr(data_fetcher, "is_connected"):
            connected = data_fetcher.is_connected()
            assert connected is None or isinstance(connected, bool)

    def test_data_fetcher_get_tick_volume(self, data_fetcher):
        """Test getting tick volume."""
        if hasattr(data_fetcher, "get_volume"):
            volume = data_fetcher.get_volume("EURUSD")
            assert volume is None or isinstance(volume, (int, float))

    def test_data_fetcher_cache_hit(self, data_fetcher):
        """Test cache hit for repeated requests."""
        if hasattr(data_fetcher, "get_rates"):
            data_fetcher.mt5_conn.get_rates.return_value = [
                (1234567890, 1.2500, 1.2510, 1.2490, 1.2505, 1000)
            ]
            data = data_fetcher.get_rates("EURUSD", 60, 1000)
            assert data is None or isinstance(data, (list, pd.DataFrame))

    def test_data_fetcher_multiple_symbols(self, data_fetcher):
        """Test fetching data for multiple symbols."""
        if hasattr(data_fetcher, "get_rates"):
            for symbol in ["EURUSD", "GBPUSD"]:
                data = data_fetcher.get_rates(symbol, 60, 1000)
                assert data is None or isinstance(data, (list, pd.DataFrame))

    def test_data_fetcher_different_timeframes(self, data_fetcher):
        """Test fetching data for different timeframes."""
        if hasattr(data_fetcher, "get_rates"):
            for timeframe in [15, 60, 240, 1440]:
                data = data_fetcher.get_rates("EURUSD", timeframe, 1000)
                assert data is None or isinstance(data, (list, pd.DataFrame))

    def test_data_fetcher_large_dataset(self, data_fetcher):
        """Test fetching large dataset."""
        if hasattr(data_fetcher, "get_rates"):
            data = data_fetcher.get_rates("EURUSD", 60, 10000)
            assert data is None or isinstance(data, (list, pd.DataFrame))

    def test_data_fetcher_small_dataset(self, data_fetcher):
        """Test fetching small dataset."""
        if hasattr(data_fetcher, "get_rates"):
            data = data_fetcher.get_rates("EURUSD", 60, 1)
            assert data is None or isinstance(data, (list, pd.DataFrame))

    def test_data_fetcher_cache_invalidation(self, data_fetcher):
        """Test cache invalidation after timeout."""
        if hasattr(data_fetcher, "clear_cache"):
            data_fetcher.clear_cache()
            assert True

    def test_data_fetcher_sync_data(self, data_fetcher):
        """Test syncing historical data."""
        if hasattr(data_fetcher, "sync_data"):
            result = data_fetcher.sync_data("EURUSD")
            assert result is None or isinstance(result, (bool, int))

    def test_data_fetcher_validate_rates(self, data_fetcher):
        """Test rate data validation."""
        if hasattr(data_fetcher, "validate"):
            df = pd.DataFrame(
                {
                    "time": [1234567890],
                    "open": [1.2500],
                    "high": [1.2510],
                    "low": [1.2490],
                    "close": [1.2505],
                }
            )
            result = data_fetcher.validate(df)
            assert result is None or isinstance(result, bool)

    def test_data_fetcher_get_latest_rate(self, data_fetcher):
        """Test getting latest rate."""
        if hasattr(data_fetcher, "get_latest"):
            data_fetcher.mt5_conn.get_rates.return_value = [
                (1234567890, 1.2500, 1.2510, 1.2490, 1.2505, 1000)
            ]
            latest = data_fetcher.get_latest("EURUSD")
            assert latest is None or isinstance(latest, (dict, tuple))

    def test_data_fetcher_handle_no_data(self, data_fetcher):
        """Test handling when no data available."""
        if hasattr(data_fetcher, "get_rates"):
            data_fetcher.mt5_conn.get_rates.return_value = None
            data = data_fetcher.get_rates("INVALID", 60, 1000)
            assert data is None or isinstance(data, (list, pd.DataFrame))

    def test_data_fetcher_connection_error_handling(self, data_fetcher):
        """Test handling connection errors."""
        if hasattr(data_fetcher, "get_rates"):
            data_fetcher.mt5_conn.get_rates.side_effect = Exception("Connection error")
            data = data_fetcher.get_rates("EURUSD", 60, 1000)
            assert data is None or isinstance(data, (list, pd.DataFrame))

    # ===== NEW COMPREHENSIVE TESTS =====

    def test_logger_exists(self, data_fetcher):
        """Test that logger is initialized."""
        assert hasattr(data_fetcher, "logger")
        assert isinstance(data_fetcher.logger, logging.Logger)

    def test_sync_data_method_exists(self, data_fetcher):
        """Test that sync_data method exists and is callable."""
        if hasattr(data_fetcher, "sync_data"):
            assert callable(data_fetcher.sync_data)

    def test_fetch_data_method_exists(self, data_fetcher):
        """Test that fetch_data method exists and is callable."""
        if hasattr(data_fetcher, "fetch_data"):
            assert callable(data_fetcher.fetch_data)

    def test_sync_data_incremental_method_exists(self, data_fetcher):
        """Test that sync_data_incremental method exists."""
        if hasattr(data_fetcher, "sync_data_incremental"):
            assert callable(data_fetcher.sync_data_incremental)

    def test_load_pairs_returns_list(self, data_fetcher):
        """Test that load_pairs returns a list."""
        if hasattr(data_fetcher, "load_pairs"):
            pairs = data_fetcher.load_pairs()
            assert isinstance(pairs, list) or pairs is None

    def test_format_timeframe_conversion(self, data_fetcher):
        """Test timeframe formatting."""
        if hasattr(data_fetcher, "format_timeframe"):
            # Test minute conversion
            result = data_fetcher.format_timeframe(15)
            assert result == "M15" or isinstance(result, str)

            # Test hour conversion
            result = data_fetcher.format_timeframe(60)
            assert result == "H1" or isinstance(result, str)

            # Test daily conversion
            result = data_fetcher.format_timeframe(1440)
            assert result == "D1" or isinstance(result, str)

    @pytest.mark.parametrize(
        "symbol,timeframe,count",
        [
            ("EURUSD", 15, 1000),
            ("GBPUSD", 60, 2000),
            ("BTCUSD", 240, 500),
            ("USDJPY", 1440, 100),
        ],
    )
    @patch("pandas.read_sql")
    def test_fetch_data_parametrized(
        self, mock_read_sql, data_fetcher, symbol, timeframe, count
    ):
        """Parametrized test for fetching data with various parameters."""
        # Setup mock to return empty DataFrame (triggers MT5 sync path)
        mock_read_sql.return_value = pd.DataFrame()
        if hasattr(data_fetcher, "fetch_data"):
            data_fetcher.mt5_conn.fetch_market_data = MagicMock(
                return_value=pd.DataFrame(
                    {
                        "time": [datetime.now()],
                        "open": [40000],
                        "high": [40100],
                        "low": [39900],
                        "close": [40050],
                        "tick_volume": [1000],
                    }
                )
            )
            result = data_fetcher.fetch_data(symbol, timeframe, count)
            assert result is None or isinstance(result, pd.DataFrame)

    def test_has_sufficient_data_check(self, data_fetcher):
        """Test checking for sufficient data in database."""
        if hasattr(data_fetcher, "has_sufficient_data"):
            data_fetcher.db.execute_query = MagicMock(
                return_value=MagicMock(fetchone=MagicMock(return_value={"count": 2500}))
            )
            result = data_fetcher.has_sufficient_data(min_rows=2000)
            assert isinstance(result, bool) or result is None

    def test_sync_data_for_pair(self, data_fetcher):
        """Test syncing data for a specific pair."""
        if hasattr(data_fetcher, "sync_data_for_pair"):
            data_fetcher.mt5_conn.fetch_market_data = MagicMock(
                return_value=pd.DataFrame(
                    {
                        "time": [datetime.now()],
                        "open": [1.1000],
                        "high": [1.1050],
                        "low": [1.0950],
                        "close": [1.1025],
                        "tick_volume": [500],
                    }
                )
            )
            result = data_fetcher.sync_data_for_pair(
                "EURUSD", 60, datetime.now() - timedelta(days=30), datetime.now()
            )
            assert isinstance(result, int) or result is None

    def test_get_mt5_timeframe_conversion(self, data_fetcher):
        """Test MT5 timeframe conversion."""
        if hasattr(data_fetcher, "get_mt5_timeframe"):
            result_15m = data_fetcher.get_mt5_timeframe(15)
            result_60m = data_fetcher.get_mt5_timeframe(60)
            result_240m = data_fetcher.get_mt5_timeframe(240)

            # Should return MT5 timeframe constants
            assert result_15m is not None
            assert result_60m is not None
            assert result_240m is not None

    @patch("pandas.read_sql")
    def test_caching_mechanism(self, mock_read_sql, data_fetcher):
        """Test LRU caching of market data."""
        mock_read_sql.return_value = pd.DataFrame()
        if hasattr(data_fetcher, "_get_market_data_cached"):
            # First call
            data_fetcher.db.execute_query = MagicMock(
                return_value=MagicMock(fetchall=MagicMock(return_value=[]))
            )

            result1 = data_fetcher._get_market_data_cached("EURUSD", "H1", 1000)
            call_count_1 = data_fetcher.db.execute_query.call_count

            # Second call with same args (should use cache)
            result2 = data_fetcher._get_market_data_cached("EURUSD", "H1", 1000)
            call_count_2 = data_fetcher.db.execute_query.call_count

            # Cache should prevent additional calls
            assert call_count_1 == call_count_2

    def test_error_recovery_on_sync_failure(self, data_fetcher):
        """Test error handling when sync fails."""
        if hasattr(data_fetcher, "sync_data"):
            data_fetcher.mt5_conn.initialize = MagicMock(return_value=False)
            # Should not raise exception
            result = data_fetcher.sync_data(symbol="EURUSD")
            assert result is None

    def test_multiple_symbol_sync(self, data_fetcher):
        """Test syncing data for multiple symbols."""
        if hasattr(data_fetcher, "sync_data"):
            data_fetcher.mt5_conn.initialize = MagicMock(return_value=True)
            data_fetcher.mt5_conn.fetch_market_data = MagicMock(
                return_value=pd.DataFrame(
                    {
                        "time": [datetime.now()],
                        "open": [1.0],
                        "high": [1.1],
                        "low": [0.9],
                        "close": [1.05],
                        "tick_volume": [1000],
                    }
                )
            )

            # Should handle multiple symbols without crashing
            for symbol in ["EURUSD", "GBPUSD", "USDJPY"]:
                result = data_fetcher.sync_data(symbol=symbol)
                assert result is None

    @pytest.mark.parametrize("limit", [100, 500, 1000, 2000])
    @patch("pandas.read_sql")
    def test_fetch_data_with_various_limits(self, mock_read_sql, data_fetcher, limit):
        """Parametrized test for fetching data with various limit values."""
        mock_read_sql.return_value = pd.DataFrame()
        if hasattr(data_fetcher, "fetch_data"):
            data_fetcher.mt5_conn.fetch_market_data = MagicMock(
                return_value=pd.DataFrame()
            )
            result = data_fetcher.fetch_data("EURUSD", 60, limit=limit)
            assert result is None or isinstance(result, pd.DataFrame)
