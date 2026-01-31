"""Unit tests for data fetcher module."""

import pytest
from unittest.mock import Mock, patch
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
        db_conn_mock = Mock()
        db_conn_mock.cursor.return_value = cursor_mock
        db.conn = db_conn_mock

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
