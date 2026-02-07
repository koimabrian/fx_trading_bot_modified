"""Centralized value validation utilities.

Provides consistent validation methods for common patterns:
- NaN/Infinity checking
- Empty DataFrame validation
- Numeric value sanitization
- Data sufficiency checks

Eliminates duplicate validation logic across 15+ files.
"""

import math
from typing import Any, Optional, Union

import numpy as np
import pandas as pd


class ValueValidator:
    """Centralized validation for data quality checks."""

    @staticmethod
    def is_valid_number(value: Any) -> bool:
        """Check if value is a valid, finite number.

        Args:
            value: Value to check (can be float, int, numpy type, or None)

        Returns:
            True if value is a valid finite number, False otherwise

        Examples:
            >>> ValueValidator.is_valid_number(1.5)
            True
            >>> ValueValidator.is_valid_number(float('nan'))
            False
            >>> ValueValidator.is_valid_number(float('inf'))
            False
            >>> ValueValidator.is_valid_number(None)
            False
        """
        if value is None:
            return False

        try:
            # Handle numpy types
            if isinstance(value, (np.floating, np.integer)):
                return not (np.isnan(value) or np.isinf(value))

            # Handle Python float/int
            if isinstance(value, (float, int)):
                if isinstance(value, float):
                    return not (math.isnan(value) or math.isinf(value))
                return True  # int is always valid

            return False
        except (TypeError, ValueError):
            return False

    @staticmethod
    def sanitize_value(
        value: Any, default: Union[int, float, str, None] = 0
    ) -> Union[int, float, str, None]:
        """Sanitize value by replacing NaN/Infinity with default.

        Args:
            value: Value to sanitize
            default: Default value to return if invalid (default: 0)

        Returns:
            Sanitized value (original if valid, default if invalid)

        Examples:
            >>> ValueValidator.sanitize_value(1.5)
            1.5
            >>> ValueValidator.sanitize_value(float('nan'))
            0
            >>> ValueValidator.sanitize_value(float('inf'), None)
            None
        """
        if value is None:
            return default

        try:
            # Handle numpy types
            if isinstance(value, (np.floating, np.integer)):
                if np.isnan(value) or np.isinf(value):
                    return default
                return value

            # Handle Python float
            if isinstance(value, float):
                if math.isnan(value) or math.isinf(value):
                    return default
                return value

            # Handle int and other types
            return value

        except (TypeError, ValueError):
            return default

    @staticmethod
    def is_dataframe_empty(df: pd.DataFrame) -> bool:
        """Check if DataFrame is None or empty.

        Args:
            df: DataFrame to check

        Returns:
            True if DataFrame is None or empty, False otherwise

        Examples:
            >>> ValueValidator.is_dataframe_empty(None)
            True
            >>> ValueValidator.is_dataframe_empty(pd.DataFrame())
            True
            >>> ValueValidator.is_dataframe_empty(pd.DataFrame({'a': [1, 2]}))
            False
        """
        return df is None or df.empty

    @staticmethod
    def has_sufficient_data(
        df: pd.DataFrame, required_rows: int, context: str = ""
    ) -> bool:
        """Check if DataFrame has sufficient rows for analysis.

        Args:
            df: DataFrame to check
            required_rows: Minimum number of rows required
            context: Optional context string for logging

        Returns:
            True if sufficient data, False otherwise

        Examples:
            >>> data = pd.DataFrame({'close': [1, 2, 3, 4, 5]})
            >>> ValueValidator.has_sufficient_data(data, 3)
            True
            >>> ValueValidator.has_sufficient_data(data, 10)
            False
        """
        if ValueValidator.is_dataframe_empty(df):
            return False

        if len(df) < required_rows:
            if context:
                from src.utils.logging_factory import LoggingFactory

                logger = LoggingFactory.get_logger(__name__)
                logger.warning(
                    "%s: Insufficient data - got %d rows, need %d",
                    context,
                    len(df),
                    required_rows,
                )
            return False

        return True

    @staticmethod
    def validate_price_data(df: pd.DataFrame) -> bool:
        """Validate that DataFrame has required OHLCV columns.

        Args:
            df: DataFrame to validate

        Returns:
            True if has required columns, False otherwise

        Examples:
            >>> data = pd.DataFrame({
            ...     'open': [1, 2], 'high': [3, 4], 'low': [0.5, 1],
            ...     'close': [2, 3], 'volume': [100, 200]
            ... })
            >>> ValueValidator.validate_price_data(data)
            True
        """
        if ValueValidator.is_dataframe_empty(df):
            return False

        required_columns = ["open", "high", "low", "close"]
        return all(col in df.columns for col in required_columns)

    @staticmethod
    def clean_numeric_dict(data: dict, default: Any = 0) -> dict:
        """Clean all numeric values in a dictionary, replacing NaN/Inf with default.

        Args:
            data: Dictionary with potentially invalid numeric values
            default: Default value for invalid numbers

        Returns:
            Dictionary with sanitized values

        Examples:
            >>> ValueValidator.clean_numeric_dict({'a': 1.5, 'b': float('nan')})
            {'a': 1.5, 'b': 0}
        """
        cleaned = {}
        for key, value in data.items():
            if isinstance(value, dict):
                cleaned[key] = ValueValidator.clean_numeric_dict(value, default)
            elif isinstance(value, (list, tuple)):
                cleaned[key] = [
                    ValueValidator.sanitize_value(v, default) for v in value
                ]
            else:
                cleaned[key] = ValueValidator.sanitize_value(value, default)
        return cleaned
