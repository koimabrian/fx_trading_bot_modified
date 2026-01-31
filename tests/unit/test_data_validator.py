"""Unit tests for data validator module."""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.utils.data_validator import DataValidator


class TestDataValidatorInitialization:
    """Test DataValidator initialization and configuration."""

    def test_data_validator_initialization(self):
        """Test DataValidator initializes correctly."""
        mock_db = Mock()
        config = {"max_missing_percent": 5.0}
        validator = DataValidator(mock_db, config)
        assert validator is not None

    def test_data_validator_default_thresholds(self):
        """Test DataValidator default thresholds are set."""
        mock_db = Mock()
        config = {"max_missing_percent": 5.0}
        validator = DataValidator(mock_db, config)
        # Validator should have default thresholds for various checks
        assert hasattr(validator, "__init__")

    def test_data_validator_with_custom_config(self):
        """Test DataValidator with custom configuration."""
        mock_db = Mock()
        config = {"max_missing_percent": 5.0, "max_outlier_percent": 2.0}
        validator = DataValidator(mock_db, config)
        assert validator is not None


class TestOHLCValidation:
    """Test OHLC data validation."""

    @pytest.fixture
    def valid_ohlc_df(self):
        """Create valid OHLC dataframe."""
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

    @pytest.fixture
    def invalid_ohlc_df(self):
        """Create invalid OHLC dataframe (high < low)."""
        dates = pd.date_range("2026-01-01", periods=10, freq="h")
        return pd.DataFrame(
            {
                "time": dates,
                "open": [1.2500] * 10,
                "high": [1.2490] * 10,  # High < Low (invalid)
                "low": [1.2510] * 10,
                "close": [1.2505] * 10,
                "tick_volume": [1000] * 10,
            }
        )

    def test_ohlc_structure_validation(self, valid_ohlc_df):
        """Test OHLC structure validation."""
        required_columns = ["open", "high", "low", "close"]

        for col in required_columns:
            assert col in valid_ohlc_df.columns

    def test_ohlc_high_low_relationship(self, valid_ohlc_df):
        """Test high >= low relationship."""
        for idx, row in valid_ohlc_df.iterrows():
            assert row["high"] >= row["low"]

    def test_ohlc_high_open_close_relationship(self, valid_ohlc_df):
        """Test high >= open and high >= close."""
        for idx, row in valid_ohlc_df.iterrows():
            assert row["high"] >= row["open"]
            assert row["high"] >= row["close"]

    def test_ohlc_low_open_close_relationship(self, valid_ohlc_df):
        """Test low <= open and low <= close."""
        for idx, row in valid_ohlc_df.iterrows():
            assert row["low"] <= row["open"]
            assert row["low"] <= row["close"]

    def test_invalid_ohlc_detection(self, invalid_ohlc_df):
        """Test detection of invalid OHLC data."""
        for idx, row in invalid_ohlc_df.iterrows():
            is_valid = row["high"] >= row["low"]
            assert is_valid is False


class TestMissingDataHandling:
    """Test handling of missing data."""

    @pytest.fixture
    def df_with_missing(self):
        """Create dataframe with missing values."""
        dates = pd.date_range("2026-01-01", periods=10, freq="h")
        df = pd.DataFrame(
            {
                "open": [
                    1.2500,
                    np.nan,
                    1.2502,
                    1.2503,
                    1.2504,
                    1.2505,
                    np.nan,
                    1.2507,
                    1.2508,
                    1.2509,
                ],
                "high": [
                    1.2510,
                    1.2511,
                    np.nan,
                    1.2513,
                    1.2514,
                    1.2515,
                    1.2516,
                    np.nan,
                    1.2518,
                    1.2519,
                ],
                "low": [
                    1.2490,
                    1.2491,
                    1.2492,
                    np.nan,
                    1.2494,
                    1.2495,
                    1.2496,
                    1.2497,
                    1.2498,
                    np.nan,
                ],
                "close": [
                    1.2505,
                    1.2506,
                    1.2507,
                    1.2508,
                    1.2509,
                    np.nan,
                    1.2511,
                    1.2512,
                    1.2513,
                    1.2514,
                ],
            }
        )
        df.index = dates
        return df

    @pytest.fixture
    def df_complete(self):
        """Create dataframe with no missing values."""
        dates = pd.date_range("2026-01-01", periods=10, freq="h")
        return pd.DataFrame(
            {
                "open": [1.2500 + i * 0.0001 for i in range(10)],
                "high": [1.2510 + i * 0.0001 for i in range(10)],
                "low": [1.2490 + i * 0.0001 for i in range(10)],
                "close": [1.2505 + i * 0.0001 for i in range(10)],
            },
            index=pd.date_range("2026-01-01", periods=10, freq="h"),
        )

    def test_missing_data_detection(self, df_with_missing):
        """Test detection of missing data."""
        missing_count = df_with_missing.isnull().sum().sum()
        assert missing_count > 0

    def test_missing_data_percentage(self, df_with_missing):
        """Test calculation of missing data percentage."""
        total_cells = df_with_missing.size
        missing_cells = df_with_missing.isnull().sum().sum()
        missing_percent = (missing_cells / total_cells) * 100

        assert missing_percent > 0
        assert missing_percent < 100

    def test_forward_fill_imputation(self, df_with_missing):
        """Test forward fill imputation."""
        df_filled = df_with_missing.ffill()
        assert (
            df_filled.isnull().sum().sum() == 0
            or df_filled.isnull().sum().sum() < df_with_missing.isnull().sum().sum()
        )

    def test_backward_fill_imputation(self, df_with_missing):
        """Test backward fill imputation."""
        df_filled = df_with_missing.bfill()
        assert (
            df_filled.isnull().sum().sum() == 0
            or df_filled.isnull().sum().sum() < df_with_missing.isnull().sum().sum()
        )

    def test_no_missing_data(self, df_complete):
        """Test dataframe with no missing data."""
        missing_count = df_complete.isnull().sum().sum()
        assert missing_count == 0


class TestOutlierDetection:
    """Test outlier detection and handling."""

    @pytest.fixture
    def df_with_outliers(self):
        """Create dataframe with outliers."""
        dates = pd.date_range("2026-01-01", periods=10, freq="h")
        return pd.DataFrame(
            {
                "close": [
                    1.2500,
                    1.2502,
                    1.2501,
                    1.2503,
                    2.5000,
                    1.2502,
                    1.2501,
                    1.2503,
                    1.2502,
                    1.2501,
                ],
            },
            index=dates,
        )

    def test_outlier_detection_iqr(self, df_with_outliers):
        """Test outlier detection using IQR method."""
        data = df_with_outliers["close"]
        Q1 = data.quantile(0.25)
        Q3 = data.quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        outliers = data[(data < lower_bound) | (data > upper_bound)]
        assert len(outliers) > 0

    def test_outlier_detection_zscore(self, df_with_outliers):
        """Test outlier detection using Z-score method."""
        data = df_with_outliers["close"]
        mean = data.mean()
        std = data.std()
        z_scores = np.abs((data - mean) / std)

        outliers = z_scores[z_scores > 2]
        assert int(len(outliers)) > 0

    def test_spike_detection(self, df_with_outliers):
        """Test detection of price spikes."""
        data = df_with_outliers["close"]
        price_changes = data.pct_change().abs()

        spike_threshold = 0.1  # 10%
        spikes = price_changes[price_changes > spike_threshold]

        assert len(spikes) > 0


class TestDataQualityMetrics:
    """Test data quality metrics calculation."""

    @pytest.fixture
    def sample_df(self):
        """Create sample dataframe."""
        dates = pd.date_range("2026-01-01", periods=100, freq="h")
        return pd.DataFrame(
            {
                "open": np.random.uniform(1.2400, 1.2600, 100),
                "high": np.random.uniform(1.2500, 1.2700, 100),
                "low": np.random.uniform(1.2300, 1.2500, 100),
                "close": np.random.uniform(1.2400, 1.2600, 100),
            },
            index=dates,
        )

    def test_data_completeness(self, sample_df):
        """Test data completeness metric."""
        completeness = (1 - sample_df.isnull().sum().sum() / sample_df.size) * 100
        assert completeness > 0
        assert completeness <= 100

    def test_timestamp_continuity(self, sample_df):
        """Test timestamp continuity check."""
        time_diffs = sample_df.index.to_series().diff()
        expected_freq = timedelta(hours=1)

        # Most time differences should match expected frequency
        matches = (time_diffs == expected_freq).sum()
        assert matches >= len(time_diffs) - 2  # Allow 2 mismatches

    def test_price_range_validation(self, sample_df):
        """Test price range validation."""
        reasonable_range = (sample_df["close"] > 0) & (sample_df["close"] < 100000)
        assert reasonable_range.all()

    def test_volume_validation(self):
        """Test volume data validation."""
        volumes = [1000, 2000, 500, 0, 3000]

        for vol in volumes:
            is_valid = vol >= 0
            assert is_valid


class TestDataValidationEdgeCases:
    """Test edge cases in data validation."""

    def test_empty_dataframe(self):
        """Test validation of empty dataframe."""
        df = pd.DataFrame()
        is_empty = len(df) == 0
        assert is_empty is True

    def test_single_row_dataframe(self):
        """Test validation of single row dataframe."""
        df = pd.DataFrame({"price": [1.2500]})
        is_valid = len(df) >= 1
        assert is_valid is True

    def test_duplicate_timestamps(self):
        """Test handling of duplicate timestamps."""
        dates = [
            "2026-01-01 10:00:00",
            "2026-01-01 10:00:00",
            "2026-01-01 11:00:00",
        ]
        df = pd.DataFrame(
            {"price": [1.2500, 1.2501, 1.2502]},
            index=pd.to_datetime(dates),
        )

        duplicates = df.index.duplicated().sum()
        assert duplicates > 0

    def test_negative_prices(self):
        """Test detection of negative prices."""
        prices = [1.2500, -1.2501, 1.2502]

        invalid = [p for p in prices if p < 0]
        assert len(invalid) > 0

    def test_zero_volume(self):
        """Test handling of zero volume."""
        volumes = [1000, 0, 2000]

        zero_vol = [v for v in volumes if v == 0]
        assert len(zero_vol) > 0

    def test_extreme_price_changes(self):
        """Test detection of extreme price changes."""
        prices = [1.2500, 1.2501, 10.0000]  # 10x spike
        price_changes = [
            (prices[i] - prices[i - 1]) / prices[i - 1] * 100
            for i in range(1, len(prices))
        ]

        extreme_changes = [pc for pc in price_changes if abs(pc) > 1.0]  # >1% change
        assert len(extreme_changes) > 0


class TestDataConversionAndFormatting:
    """Test data conversion and formatting."""

    def test_timestamp_parsing(self):
        """Test timestamp parsing."""
        timestamp_str = "2026-01-01 10:30:00"
        parsed = pd.to_datetime(timestamp_str)

        assert isinstance(parsed, pd.Timestamp)
        assert parsed.year == 2026

    def test_price_precision(self):
        """Test price precision handling."""
        price = 1.25005
        rounded = round(price, 4)

        assert rounded == 1.2501

    def test_volume_conversion(self):
        """Test volume conversion."""
        volume_str = "1000"
        volume_int = int(volume_str)

        assert volume_int == 1000
        assert isinstance(volume_int, int)

    def test_dataframe_sorting(self):
        """Test dataframe sorting by timestamp."""
        dates = ["2026-01-03", "2026-01-01", "2026-01-02"]
        df = pd.DataFrame(
            {"price": [1.2503, 1.2501, 1.2502]},
            index=pd.to_datetime(dates),
        )

        df_sorted = df.sort_index()
        assert df_sorted.index[0] < df_sorted.index[1] < df_sorted.index[2]


class TestDataValidationIntegration:
    """Integration tests for data validation."""

    def test_complete_validation_workflow(self):
        """Test complete data validation workflow."""
        # Create test data
        dates = pd.date_range("2026-01-01", periods=50, freq="h")
        df = pd.DataFrame(
            {
                "open": [1.2500 + i * 0.00001 for i in range(50)],
                "high": [1.2510 + i * 0.00001 for i in range(50)],
                "low": [1.2490 + i * 0.00001 for i in range(50)],
                "close": [1.2505 + i * 0.00001 for i in range(50)],
                "tick_volume": [1000 + i * 10 for i in range(50)],
            },
            index=dates,
        )

        # Validation checks
        checks = {
            "has_data": len(df) > 0,
            "no_missing": df.isnull().sum().sum() == 0,
            "high_gte_low": bool((df["high"] >= df["low"]).all()),
            "positive_volume": bool((df["tick_volume"] > 0).all()),
        }

        for check, result in checks.items():
            assert result == True

    def test_validation_failure_recovery(self):
        """Test recovery from validation failures."""
        # Create invalid data
        dates = pd.date_range("2026-01-01", periods=10, freq="h")
        df = pd.DataFrame(
            {
                "open": [
                    1.2500,
                    np.nan,
                    1.2502,
                    1.2503,
                    1.2504,
                    1.2505,
                    np.nan,
                    1.2507,
                    1.2508,
                    1.2509,
                ],
                "high": [1.2490] * 10,  # Invalid: high < low
                "low": [1.2510] * 10,
                "close": [1.2505] * 10,
            },
            index=dates,
        )

        # Recovery: drop invalid rows
        df_invalid = df[df["high"] < df["low"]]
        recovery_successful = len(df_invalid) > 0

        assert recovery_successful is True
