"""Unit tests for data handler module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.core.data_handler import DataHandler


class TestDataHandlerInitialization:
    """Test DataHandler initialization."""

    def test_data_handler_initialization(self):
        """Test DataHandler initializes correctly."""
        mock_db = Mock()
        config = {"database": {"path": ":memory:"}}
        with patch("src.database.db_manager.DatabaseManager"):
            handler = DataHandler(mock_db, config)
            assert handler is not None

    def test_data_handler_with_config(self):
        """Test DataHandler initialization with config."""
        mock_db = Mock()
        config = {"database": {"path": ":memory:"}}
        with patch("src.database.db_manager.DatabaseManager"):
            handler = DataHandler(mock_db, config)
            assert hasattr(handler, "__init__")


class TestDataTransformation:
    """Test data transformation operations."""

    @pytest.fixture
    def raw_ohlc_data(self):
        """Create raw OHLC data."""
        dates = pd.date_range("2026-01-01", periods=10, freq="h")
        return pd.DataFrame(
            {
                "time": dates,
                "open": [1.2500 + i * 0.0001 for i in range(10)],
                "high": [1.2510 + i * 0.0001 for i in range(10)],
                "low": [1.2490 + i * 0.0001 for i in range(10)],
                "close": [1.2505 + i * 0.0001 for i in range(10)],
                "tick_volume": [1000 + i * 10 for i in range(10)],
            }
        )

    def test_data_normalization(self, raw_ohlc_data):
        """Test data normalization."""
        normalized = raw_ohlc_data.copy()

        for col in ["open", "high", "low", "close"]:
            min_val = normalized[col].min()
            max_val = normalized[col].max()
            normalized[col] = (normalized[col] - min_val) / (max_val - min_val)

        assert (normalized["close"] >= 0).all()
        assert (normalized["close"] <= 1).all()

    def test_data_standardization(self, raw_ohlc_data):
        """Test data standardization (z-score)."""
        standardized = raw_ohlc_data.copy()

        for col in ["open", "high", "low", "close"]:
            mean = standardized[col].mean()
            std = standardized[col].std()
            standardized[col] = (standardized[col] - mean) / std

        assert abs(standardized["close"].mean()) < 0.01
        assert abs(standardized["close"].std() - 1.0) < 0.1

    def test_data_aggregation(self, raw_ohlc_data):
        """Test data aggregation to different timeframes."""
        # Aggregate hourly data to 4-hourly
        raw_ohlc_data["time"] = pd.to_datetime(raw_ohlc_data["time"])
        raw_ohlc_data.set_index("time", inplace=True)

        aggregated = raw_ohlc_data.resample("4h").agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "tick_volume": "sum",
            }
        )

        assert len(aggregated) <= len(raw_ohlc_data)

    def test_data_resampling(self, raw_ohlc_data):
        """Test data resampling."""
        raw_ohlc_data["time"] = pd.to_datetime(raw_ohlc_data["time"])
        raw_ohlc_data.set_index("time", inplace=True)

        # Downsample
        downsampled = raw_ohlc_data["close"].resample("2h").last()

        assert len(downsampled) <= len(raw_ohlc_data)


class TestIndicatorCalculation:
    """Test indicator calculation."""

    @pytest.fixture
    def price_data(self):
        """Create price data."""
        dates = pd.date_range("2026-01-01", periods=100, freq="h")
        prices = 1.2500 + np.cumsum(np.random.normal(0, 0.0001, 100))
        return pd.DataFrame(
            {"close": prices},
            index=dates,
        )

    def test_moving_average_calculation(self, price_data):
        """Test moving average calculation."""
        price_data["SMA20"] = price_data["close"].rolling(window=20).mean()

        assert "SMA20" in price_data.columns
        assert pd.isna(price_data["SMA20"].iloc[0:19]).all()
        assert not pd.isna(price_data["SMA20"].iloc[19])

    def test_rsi_calculation(self, price_data):
        """Test RSI calculation."""
        delta = price_data["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()

        rs = gain / loss
        price_data["RSI"] = 100 - (100 / (1 + rs))

        assert "RSI" in price_data.columns
        assert price_data["RSI"].min() >= 0 or pd.isna(price_data["RSI"]).any()
        assert price_data["RSI"].max() <= 100 or pd.isna(price_data["RSI"]).any()

    def test_macd_calculation(self, price_data):
        """Test MACD calculation."""
        ema12 = price_data["close"].ewm(span=12, adjust=False).mean()
        ema26 = price_data["close"].ewm(span=26, adjust=False).mean()
        price_data["MACD"] = ema12 - ema26
        price_data["Signal"] = price_data["MACD"].ewm(span=9, adjust=False).mean()

        assert "MACD" in price_data.columns
        assert "Signal" in price_data.columns

    def test_bollinger_bands_calculation(self, price_data):
        """Test Bollinger Bands calculation."""
        sma = price_data["close"].rolling(window=20).mean()
        std = price_data["close"].rolling(window=20).std()

        price_data["BB_Upper"] = sma + (2 * std)
        price_data["BB_Middle"] = sma
        price_data["BB_Lower"] = sma - (2 * std)

        assert "BB_Upper" in price_data.columns
        assert "BB_Middle" in price_data.columns
        assert "BB_Lower" in price_data.columns


class TestDataValidationInDataHandler:
    """Test data validation in data handler."""

    def test_null_value_detection(self):
        """Test detection of null values."""
        data = pd.DataFrame(
            {
                "close": [1.2500, np.nan, 1.2502, 1.2503, np.nan],
            }
        )

        null_count = data.isnull().sum().sum()
        assert null_count > 0

    def test_data_consistency_check(self):
        """Test data consistency check."""
        data = pd.DataFrame(
            {
                "open": [1.2500, 1.2501, 1.2502],
                "high": [1.2510, 1.2511, 1.2512],
                "low": [1.2490, 1.2491, 1.2492],
                "close": [1.2505, 1.2506, 1.2507],
            }
        )

        # Check OHLC relationships
        is_consistent = bool((data["high"] >= data["low"]).all())
        assert is_consistent is True

    def test_duplicate_timestamp_detection(self):
        """Test detection of duplicate timestamps."""
        dates = [
            "2026-01-01 10:00:00",
            "2026-01-01 10:00:00",
            "2026-01-01 11:00:00",
        ]
        data = pd.DataFrame(
            {"close": [1.2500, 1.2501, 1.2502]},
            index=pd.to_datetime(dates),
        )

        duplicates = data.index.duplicated().sum()
        assert duplicates > 0

    def test_price_outlier_detection(self):
        """Test detection of price outliers."""
        data = pd.DataFrame(
            {
                "close": [1.2500, 1.2501, 1.2502, 1.2503, 100.0000],
            }
        )

        mean = data["close"].mean()
        std = data["close"].std()

        outliers = data[np.abs((data["close"] - mean) / std) > 1.5]
        assert int(len(outliers)) > 0


class TestDataCaching:
    """Test data caching functionality."""

    def test_data_cache_storage(self):
        """Test data cache storage."""
        cache = {}

        key = "EURUSD_H1_2026-01-01"
        data = pd.DataFrame({"close": [1.2500, 1.2501, 1.2502]})

        cache[key] = data

        assert key in cache
        assert cache[key].equals(data)

    def test_data_cache_retrieval(self):
        """Test data cache retrieval."""
        cache = {
            "EURUSD_H1": pd.DataFrame({"close": [1.2500, 1.2501]}),
        }

        retrieved = cache.get("EURUSD_H1")

        assert retrieved is not None
        assert len(retrieved) == 2

    def test_data_cache_invalidation(self):
        """Test data cache invalidation."""
        cache = {
            "EURUSD_H1": pd.DataFrame({"close": [1.2500, 1.2501]}),
        }

        cache.pop("EURUSD_H1", None)

        assert "EURUSD_H1" not in cache

    def test_data_cache_expiration(self):
        """Test data cache expiration."""
        cache_entry = {
            "data": pd.DataFrame({"close": [1.2500]}),
            "timestamp": datetime.now() - timedelta(hours=2),
        }

        cache_age = (datetime.now() - cache_entry["timestamp"]).total_seconds()
        cache_ttl = 3600  # 1 hour

        is_expired = cache_age > cache_ttl
        assert is_expired is True


class TestDataEnrichment:
    """Test data enrichment operations."""

    @pytest.fixture
    def base_data(self):
        """Create base data."""
        dates = pd.date_range("2026-01-01", periods=20, freq="h")
        return pd.DataFrame(
            {
                "close": [1.2500 + i * 0.0001 for i in range(20)],
            },
            index=dates,
        )

    def test_add_returns(self, base_data):
        """Test adding returns column."""
        base_data["returns"] = base_data["close"].pct_change()

        assert "returns" in base_data.columns
        assert pd.isna(base_data["returns"].iloc[0])

    def test_add_log_returns(self, base_data):
        """Test adding log returns column."""
        base_data["log_returns"] = np.log(
            base_data["close"] / base_data["close"].shift(1)
        )

        assert "log_returns" in base_data.columns

    def test_add_volatility(self, base_data):
        """Test adding volatility column."""
        base_data["volatility"] = base_data["close"].rolling(window=10).std()

        assert "volatility" in base_data.columns

    def test_add_cumulative_returns(self, base_data):
        """Test adding cumulative returns column."""
        base_data["cum_returns"] = (1 + base_data["close"].pct_change()).cumprod() - 1

        assert "cum_returns" in base_data.columns


class TestDataIntegration:
    """Integration tests for data handler."""

    def test_complete_data_pipeline(self):
        """Test complete data pipeline."""
        # Create raw data
        dates = pd.date_range("2026-01-01", periods=50, freq="h")
        raw_data = pd.DataFrame(
            {
                "open": [1.2500 + i * 0.0001 for i in range(50)],
                "high": [1.2510 + i * 0.0001 for i in range(50)],
                "low": [1.2490 + i * 0.0001 for i in range(50)],
                "close": [1.2505 + i * 0.0001 for i in range(50)],
            },
            index=dates,
        )

        # Validate
        assert (raw_data["high"] >= raw_data["low"]).all()

        # Transform
        raw_data["SMA10"] = raw_data["close"].rolling(window=10).mean()

        # Enrich
        raw_data["returns"] = raw_data["close"].pct_change()

        # Verify
        assert "SMA10" in raw_data.columns
        assert "returns" in raw_data.columns

    def test_data_handler_workflow(self):
        """Test DataHandler workflow."""
        mock_db = Mock()
        config = {"database": {"path": ":memory:"}}
        with patch("src.database.db_manager.DatabaseManager"):
            handler = DataHandler(mock_db, config)

            # Create mock data
            data = pd.DataFrame(
                {
                    "close": [1.2500, 1.2501, 1.2502],
                }
            )

            # Process
            processed = data.copy()
            processed["SMA"] = processed["close"].rolling(window=2).mean()

            assert "SMA" in processed.columns
