"""Centralized technical indicator calculations.

This module provides canonical implementations of common technical indicators
to eliminate duplication and ensure consistency across the codebase.

All indicators follow the same pattern:
- Accept pandas DataFrame or Series as input
- Return pandas Series with calculated values
- Handle edge cases (insufficient data, missing columns)
- Use ta-lib library for consistency
"""

import pandas as pd
import ta
from typing import Optional

from src.utils.logging_factory import LoggingFactory


logger = LoggingFactory.get_logger(__name__)


def calculate_atr(
    data: pd.DataFrame,
    period: int = 14,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close"
) -> pd.Series:
    """Calculate Average True Range (ATR) for volatility measurement.
    
    This is the canonical ATR calculation used throughout the codebase.
    Use this function instead of directly calling ta.volatility.AverageTrueRange.
    
    Args:
        data: DataFrame with OHLC columns
        period: ATR period (default: 14)
        high_col: Name of high price column (default: "high")
        low_col: Name of low price column (default: "low")
        close_col: Name of close price column (default: "close")
        
    Returns:
        Series with ATR values (0 if calculation fails or insufficient data)
        
    Example:
        >>> data['atr'] = calculate_atr(data, period=14)
        >>> latest_atr = calculate_atr(data).iloc[-1]
    """
    try:
        # Validate inputs
        if data.empty:
            logger.warning("Empty DataFrame provided to calculate_atr")
            return pd.Series(0, index=data.index)
        
        required_cols = [high_col, low_col, close_col]
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            logger.error(f"Missing required columns for ATR: {missing_cols}")
            return pd.Series(0, index=data.index)
        
        if len(data) < period:
            logger.warning(
                f"Insufficient data for ATR: {len(data)} rows, need {period}"
            )
            return pd.Series(0, index=data.index)
        
        # Calculate ATR using ta library
        atr_indicator = ta.volatility.AverageTrueRange(
            high=data[high_col],
            low=data[low_col],
            close=data[close_col],
            window=period,
        )
        
        return atr_indicator.average_true_range().fillna(0)
        
    except (ValueError, KeyError, TypeError) as e:
        logger.error(f"Failed to calculate ATR: {e}")
        return pd.Series(0, index=data.index)


def calculate_rsi(
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """Calculate Relative Strength Index (RSI).
    
    This is the canonical RSI calculation used throughout the codebase.
    Use this function instead of directly calling ta.momentum.RSIIndicator.
    
    Args:
        close: Series of close prices
        period: RSI period (default: 14)
        
    Returns:
        Series with RSI values (0 if calculation fails or insufficient data)
        
    Example:
        >>> data['rsi'] = calculate_rsi(data['close'], period=14)
        >>> current_rsi = calculate_rsi(data['close']).iloc[-1]
    """
    try:
        # Validate inputs
        if close.empty:
            logger.warning("Empty Series provided to calculate_rsi")
            return pd.Series(0, index=close.index)
        
        if len(close) < period:
            logger.warning(
                f"Insufficient data for RSI: {len(close)} rows, need {period}"
            )
            return pd.Series(0, index=close.index)
        
        # Calculate RSI using ta library
        rsi_indicator = ta.momentum.RSIIndicator(close, window=period)
        
        return rsi_indicator.rsi().fillna(0)
        
    except (ValueError, KeyError, TypeError) as e:
        logger.error(f"Failed to calculate RSI: {e}")
        return pd.Series(0, index=close.index)


def calculate_macd(
    close: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        close: Series of close prices
        fast_period: Fast EMA period (default: 12)
        slow_period: Slow EMA period (default: 26)
        signal_period: Signal line period (default: 9)
        
    Returns:
        Tuple of (macd_line, signal_line, histogram)
        
    Example:
        >>> macd, signal, histogram = calculate_macd(data['close'])
        >>> data['macd'] = macd
        >>> data['macd_signal'] = signal
        >>> data['macd_histogram'] = histogram
    """
    try:
        if close.empty:
            logger.warning("Empty Series provided to calculate_macd")
            zero_series = pd.Series(0, index=close.index)
            return zero_series, zero_series, zero_series
        
        min_period = max(fast_period, slow_period) + signal_period
        if len(close) < min_period:
            logger.warning(
                f"Insufficient data for MACD: {len(close)} rows, need {min_period}"
            )
            zero_series = pd.Series(0, index=close.index)
            return zero_series, zero_series, zero_series
        
        # Calculate MACD using ta library
        macd_indicator = ta.trend.MACD(
            close=close,
            window_fast=fast_period,
            window_slow=slow_period,
            window_sign=signal_period
        )
        
        macd_line = macd_indicator.macd().fillna(0)
        signal_line = macd_indicator.macd_signal().fillna(0)
        histogram = macd_indicator.macd_diff().fillna(0)
        
        return macd_line, signal_line, histogram
        
    except (ValueError, KeyError, TypeError) as e:
        logger.error(f"Failed to calculate MACD: {e}")
        zero_series = pd.Series(0, index=close.index)
        return zero_series, zero_series, zero_series


def calculate_ema(
    close: pd.Series,
    period: int = 20
) -> pd.Series:
    """Calculate Exponential Moving Average (EMA).
    
    Args:
        close: Series of close prices
        period: EMA period (default: 20)
        
    Returns:
        Series with EMA values
        
    Example:
        >>> data['ema_20'] = calculate_ema(data['close'], period=20)
        >>> data['ema_50'] = calculate_ema(data['close'], period=50)
    """
    try:
        if close.empty:
            logger.warning("Empty Series provided to calculate_ema")
            return pd.Series(0, index=close.index)
        
        if len(close) < period:
            logger.warning(
                f"Insufficient data for EMA: {len(close)} rows, need {period}"
            )
            return pd.Series(0, index=close.index)
        
        # Calculate EMA using ta library
        ema_indicator = ta.trend.EMAIndicator(close=close, window=period)
        
        return ema_indicator.ema_indicator().fillna(0)
        
    except (ValueError, KeyError, TypeError) as e:
        logger.error(f"Failed to calculate EMA: {e}")
        return pd.Series(0, index=close.index)


def calculate_bollinger_bands(
    close: pd.Series,
    period: int = 20,
    std_dev: float = 2.0
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands.
    
    Args:
        close: Series of close prices
        period: Period for moving average (default: 20)
        std_dev: Standard deviation multiplier (default: 2.0)
        
    Returns:
        Tuple of (upper_band, middle_band, lower_band)
        
    Example:
        >>> upper, middle, lower = calculate_bollinger_bands(data['close'])
        >>> data['bb_upper'] = upper
        >>> data['bb_middle'] = middle
        >>> data['bb_lower'] = lower
    """
    try:
        if close.empty:
            logger.warning("Empty Series provided to calculate_bollinger_bands")
            zero_series = pd.Series(0, index=close.index)
            return zero_series, zero_series, zero_series
        
        if len(close) < period:
            logger.warning(
                f"Insufficient data for Bollinger Bands: {len(close)} rows, need {period}"
            )
            zero_series = pd.Series(0, index=close.index)
            return zero_series, zero_series, zero_series
        
        # Calculate Bollinger Bands using ta library
        bb_indicator = ta.volatility.BollingerBands(
            close=close,
            window=period,
            window_dev=std_dev
        )
        
        upper = bb_indicator.bollinger_hband().fillna(0)
        middle = bb_indicator.bollinger_mavg().fillna(0)
        lower = bb_indicator.bollinger_lband().fillna(0)
        
        return upper, middle, lower
        
    except (ValueError, KeyError, TypeError) as e:
        logger.error(f"Failed to calculate Bollinger Bands: {e}")
        zero_series = pd.Series(0, index=close.index)
        return zero_series, zero_series, zero_series


def calculate_stochastic(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3
) -> tuple[pd.Series, pd.Series]:
    """Calculate Stochastic Oscillator.
    
    Args:
        high: Series of high prices
        low: Series of low prices
        close: Series of close prices
        k_period: Period for %K line (default: 14)
        d_period: Period for %D line (default: 3)
        
    Returns:
        Tuple of (%K, %D)
        
    Example:
        >>> k, d = calculate_stochastic(data['high'], data['low'], data['close'])
        >>> data['stoch_k'] = k
        >>> data['stoch_d'] = d
    """
    try:
        if high.empty or low.empty or close.empty:
            logger.warning("Empty Series provided to calculate_stochastic")
            zero_series = pd.Series(0, index=close.index)
            return zero_series, zero_series
        
        min_period = k_period + d_period
        if len(close) < min_period:
            logger.warning(
                f"Insufficient data for Stochastic: {len(close)} rows, need {min_period}"
            )
            zero_series = pd.Series(0, index=close.index)
            return zero_series, zero_series
        
        # Calculate Stochastic using ta library
        stoch_indicator = ta.momentum.StochasticOscillator(
            high=high,
            low=low,
            close=close,
            window=k_period,
            smooth_window=d_period
        )
        
        k_line = stoch_indicator.stoch().fillna(0)
        d_line = stoch_indicator.stoch_signal().fillna(0)
        
        return k_line, d_line
        
    except (ValueError, KeyError, TypeError) as e:
        logger.error(f"Failed to calculate Stochastic: {e}")
        zero_series = pd.Series(0, index=close.index)
        return zero_series, zero_series
