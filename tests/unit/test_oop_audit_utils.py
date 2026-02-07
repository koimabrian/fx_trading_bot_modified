"""Test new utility modules added in OOP audit."""
import pandas as pd
import numpy as np


class TestValueValidator:
    """Test ValueValidator utility functions."""

    def test_is_valid_number_with_valid_float(self):
        """Test is_valid_number with valid float."""
        from src.utils.value_validator import ValueValidator
        assert ValueValidator.is_valid_number(1.5) is True
        assert ValueValidator.is_valid_number(0.0) is True
        assert ValueValidator.is_valid_number(-10.5) is True

    def test_is_valid_number_with_nan(self):
        """Test is_valid_number with NaN."""
        from src.utils.value_validator import ValueValidator
        assert ValueValidator.is_valid_number(float('nan')) is False
        assert ValueValidator.is_valid_number(np.nan) is False

    def test_is_valid_number_with_infinity(self):
        """Test is_valid_number with infinity."""
        from src.utils.value_validator import ValueValidator
        assert ValueValidator.is_valid_number(float('inf')) is False
        assert ValueValidator.is_valid_number(float('-inf')) is False

    def test_is_valid_number_with_none(self):
        """Test is_valid_number with None."""
        from src.utils.value_validator import ValueValidator
        assert ValueValidator.is_valid_number(None) is False

    def test_is_valid_number_with_int(self):
        """Test is_valid_number with integer."""
        from src.utils.value_validator import ValueValidator
        assert ValueValidator.is_valid_number(42) is True
        assert ValueValidator.is_valid_number(0) is True
        assert ValueValidator.is_valid_number(-5) is True

    def test_sanitize_value_valid(self):
        """Test sanitize_value with valid number."""
        from src.utils.value_validator import ValueValidator
        assert ValueValidator.sanitize_value(1.5) == 1.5
        assert ValueValidator.sanitize_value(42) == 42

    def test_sanitize_value_nan(self):
        """Test sanitize_value with NaN."""
        from src.utils.value_validator import ValueValidator
        assert ValueValidator.sanitize_value(float('nan')) == 0
        assert ValueValidator.sanitize_value(float('nan'), default=None) is None

    def test_sanitize_value_infinity(self):
        """Test sanitize_value with infinity."""
        from src.utils.value_validator import ValueValidator
        assert ValueValidator.sanitize_value(float('inf')) == 0
        assert ValueValidator.sanitize_value(float('-inf'), default=-1) == -1

    def test_is_dataframe_empty_with_none(self):
        """Test is_dataframe_empty with None."""
        from src.utils.value_validator import ValueValidator
        assert ValueValidator.is_dataframe_empty(None) is True

    def test_is_dataframe_empty_with_empty_df(self):
        """Test is_dataframe_empty with empty DataFrame."""
        from src.utils.value_validator import ValueValidator
        df = pd.DataFrame()
        assert ValueValidator.is_dataframe_empty(df) is True

    def test_is_dataframe_empty_with_data(self):
        """Test is_dataframe_empty with data."""
        from src.utils.value_validator import ValueValidator
        df = pd.DataFrame({'a': [1, 2, 3]})
        assert ValueValidator.is_dataframe_empty(df) is False

    def test_has_sufficient_data_true(self):
        """Test has_sufficient_data with enough rows."""
        from src.utils.value_validator import ValueValidator
        df = pd.DataFrame({'close': [1, 2, 3, 4, 5]})
        assert ValueValidator.has_sufficient_data(df, 3) is True

    def test_has_sufficient_data_false(self):
        """Test has_sufficient_data with insufficient rows."""
        from src.utils.value_validator import ValueValidator
        df = pd.DataFrame({'close': [1, 2]})
        assert ValueValidator.has_sufficient_data(df, 10) is False

    def test_has_sufficient_data_empty(self):
        """Test has_sufficient_data with empty DataFrame."""
        from src.utils.value_validator import ValueValidator
        df = pd.DataFrame()
        assert ValueValidator.has_sufficient_data(df, 5) is False

    def test_validate_price_data_valid(self):
        """Test validate_price_data with valid OHLC data."""
        from src.utils.value_validator import ValueValidator
        df = pd.DataFrame({
            'open': [1, 2],
            'high': [3, 4],
            'low': [0.5, 1],
            'close': [2, 3],
            'volume': [100, 200]
        })
        assert ValueValidator.validate_price_data(df) is True

    def test_validate_price_data_missing_columns(self):
        """Test validate_price_data with missing columns."""
        from src.utils.value_validator import ValueValidator
        df = pd.DataFrame({'open': [1, 2], 'close': [2, 3]})
        assert ValueValidator.validate_price_data(df) is False

    def test_clean_numeric_dict(self):
        """Test clean_numeric_dict."""
        from src.utils.value_validator import ValueValidator
        data = {
            'a': 1.5,
            'b': float('nan'),
            'c': float('inf'),
            'd': None,
            'e': 42
        }
        cleaned = ValueValidator.clean_numeric_dict(data, default=0)
        assert cleaned['a'] == 1.5
        assert cleaned['b'] == 0
        assert cleaned['c'] == 0
        assert cleaned['d'] == 0
        assert cleaned['e'] == 42

    def test_clean_numeric_dict_nested(self):
        """Test clean_numeric_dict with nested dict."""
        from src.utils.value_validator import ValueValidator
        data = {
            'outer': {
                'inner': float('nan'),
                'valid': 5.0
            }
        }
        cleaned = ValueValidator.clean_numeric_dict(data, default=0)
        assert cleaned['outer']['inner'] == 0
        assert cleaned['outer']['valid'] == 5.0


class TestTimeframeUtils:
    """Test timeframe utility functions."""

    def test_format_timeframe_minutes(self):
        """Test format_timeframe with minutes."""
        from src.utils.timeframe_utils import format_timeframe
        assert format_timeframe(15) == "M15"
        assert format_timeframe(60) == "H1"
        assert format_timeframe(240) == "H4"

    def test_parse_timeframe_minutes(self):
        """Test parse_timeframe with M notation."""
        from src.utils.timeframe_utils import parse_timeframe
        assert parse_timeframe("M15") == 15
        assert parse_timeframe("M5") == 5

    def test_parse_timeframe_hours(self):
        """Test parse_timeframe with H notation."""
        from src.utils.timeframe_utils import parse_timeframe
        assert parse_timeframe("H1") == 60
        assert parse_timeframe("H4") == 240

    def test_parse_timeframe_days(self):
        """Test parse_timeframe with D notation."""
        from src.utils.timeframe_utils import parse_timeframe
        assert parse_timeframe("D1") == 1440

    def test_normalize_timeframe_string(self):
        """Test normalize_timeframe with string."""
        from src.utils.timeframe_utils import normalize_timeframe
        assert normalize_timeframe("H1") == 60
        assert normalize_timeframe("M15") == 15

    def test_normalize_timeframe_int(self):
        """Test normalize_timeframe with integer."""
        from src.utils.timeframe_utils import normalize_timeframe
        assert normalize_timeframe(60) == 60
        assert normalize_timeframe(15) == 15

    def test_minutes_to_mt5_timeframe(self):
        """Test minutes_to_mt5_timeframe."""
        from src.utils.timeframe_utils import minutes_to_mt5_timeframe
        import MetaTrader5 as mt5
        
        assert minutes_to_mt5_timeframe(15) == mt5.TIMEFRAME_M15
        assert minutes_to_mt5_timeframe(60) == mt5.TIMEFRAME_H1
        assert minutes_to_mt5_timeframe(240) == mt5.TIMEFRAME_H4

    def test_mt5_timeframe_to_minutes(self):
        """Test mt5_timeframe_to_minutes."""
        from src.utils.timeframe_utils import mt5_timeframe_to_minutes
        import MetaTrader5 as mt5
        
        assert mt5_timeframe_to_minutes(mt5.TIMEFRAME_M15) == 15
        assert mt5_timeframe_to_minutes(mt5.TIMEFRAME_H1) == 60
        assert mt5_timeframe_to_minutes(mt5.TIMEFRAME_H4) == 240

    def test_mt5_timeframe_to_minutes_raw_constants(self):
        """Test mt5_timeframe_to_minutes with raw MT5 constants."""
        from src.utils.timeframe_utils import mt5_timeframe_to_minutes
        
        # Raw MT5 constants
        assert mt5_timeframe_to_minutes(16385) == 60  # H1
        assert mt5_timeframe_to_minutes(16388) == 240  # H4
