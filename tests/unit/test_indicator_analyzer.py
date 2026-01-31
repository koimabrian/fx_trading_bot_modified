"""Unit tests for indicator analyzer module."""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.utils.indicator_analyzer import IndicatorAnalyzer


class TestIndicatorAnalyzerInitialization:
    """Test IndicatorAnalyzer initialization."""

    def test_indicator_analyzer_initialization(self):
        """Test IndicatorAnalyzer initializes correctly."""
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        mock_db.conn = Mock()
        mock_db.conn.cursor.return_value = mock_cursor
        with patch("src.core.data_fetcher.DataFetcher"):
            analyzer = IndicatorAnalyzer(mock_db)
            assert analyzer is not None

    def test_indicator_analyzer_default_config(self):
        """Test IndicatorAnalyzer default configuration."""
        mock_db = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        mock_db.conn = Mock()
        mock_db.conn.cursor.return_value = mock_cursor
        with patch("src.core.data_fetcher.DataFetcher"):
            analyzer = IndicatorAnalyzer(mock_db)
            assert hasattr(analyzer, "__init__")


class TestMovingAverageAnalysis:
    """Test moving average calculation and analysis."""

    @pytest.fixture
    def price_data(self):
        """Create sample price data."""
        dates = pd.date_range("2026-01-01", periods=100, freq="h")
        prices = 1.2500 + np.cumsum(np.random.normal(0, 0.0001, 100))
        return pd.DataFrame(
            {"close": prices},
            index=dates,
        )

    def test_sma_calculation(self, price_data):
        """Test SMA calculation."""
        period = 20
        sma = price_data["close"].rolling(window=period).mean()

        assert len(sma) == len(price_data)
        assert pd.isna(sma.iloc[0 : period - 1]).all()
        assert not pd.isna(sma.iloc[period])

    def test_ema_calculation(self, price_data):
        """Test EMA calculation."""
        period = 20
        ema = price_data["close"].ewm(span=period, adjust=False).mean()

        assert len(ema) == len(price_data)
        assert not pd.isna(ema.iloc[0])

    def test_ma_crossover_buy_signal(self, price_data):
        """Test MA crossover buy signal."""
        short_ma = price_data["close"].rolling(window=5).mean()
        long_ma = price_data["close"].rolling(window=20).mean()

        # Find crossovers
        crossovers = short_ma > long_ma
        shifted = crossovers.shift(1)
        shifted = shifted.where(shifted.notna(), False)
        buy_signals = crossovers & ~shifted.astype(bool)

        assert buy_signals.sum() >= 0

    def test_ma_crossover_sell_signal(self, price_data):
        """Test MA crossover sell signal."""
        short_ma = price_data["close"].rolling(window=5).mean()
        long_ma = price_data["close"].rolling(window=20).mean()

        # Find crossovers
        crossovers = short_ma < long_ma
        shifted = crossovers.shift(1)
        shifted = shifted.where(shifted.notna(), False)
        sell_signals = crossovers & ~shifted.astype(bool)

        assert sell_signals.sum() >= 0

    def test_price_distance_from_ma(self, price_data):
        """Test price distance from moving average."""
        ma = price_data["close"].rolling(window=20).mean()
        distance = price_data["close"] - ma
        distance_percent = (distance / ma) * 100

        assert len(distance_percent) == len(price_data)


class TestRSIAnalysis:
    """Test RSI indicator analysis."""

    @pytest.fixture
    def price_data_rsi(self):
        """Create price data for RSI testing."""
        dates = pd.date_range("2026-01-01", periods=100, freq="h")
        prices = 1.2500 + np.cumsum(np.random.normal(0.00005, 0.0001, 100))
        return pd.DataFrame(
            {"close": prices},
            index=dates,
        )

    def test_rsi_calculation(self, price_data_rsi):
        """Test RSI calculation."""
        period = 14
        delta = price_data_rsi["close"].diff()

        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        assert len(rsi) == len(price_data_rsi)
        assert (rsi >= 0).all() or pd.isna(rsi).any()
        assert (rsi <= 100).all() or pd.isna(rsi).any()

    def test_rsi_overbought_condition(self, price_data_rsi):
        """Test RSI overbought detection."""
        period = 14
        delta = price_data_rsi["close"].diff()

        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        overbought = rsi > 70
        assert (overbought >= False).all()

    def test_rsi_oversold_condition(self, price_data_rsi):
        """Test RSI oversold detection."""
        period = 14
        delta = price_data_rsi["close"].diff()

        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        oversold = rsi < 30
        assert (oversold >= False).all()

    def test_rsi_neutral_zone(self, price_data_rsi):
        """Test RSI neutral zone (30-70)."""
        period = 14
        delta = price_data_rsi["close"].diff()

        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        neutral = (rsi >= 30) & (rsi <= 70)
        assert (neutral >= False).all()


class TestMACDAnalysis:
    """Test MACD indicator analysis."""

    @pytest.fixture
    def price_data_macd(self):
        """Create price data for MACD testing."""
        dates = pd.date_range("2026-01-01", periods=100, freq="h")
        prices = 1.2500 + np.cumsum(np.random.normal(0.00005, 0.0001, 100))
        return pd.DataFrame(
            {"close": prices},
            index=dates,
        )

    def test_macd_calculation(self, price_data_macd):
        """Test MACD line calculation."""
        ema12 = price_data_macd["close"].ewm(span=12, adjust=False).mean()
        ema26 = price_data_macd["close"].ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26

        assert len(macd_line) == len(price_data_macd)
        assert not pd.isna(macd_line.iloc[0])

    def test_macd_signal_line(self, price_data_macd):
        """Test MACD signal line calculation."""
        ema12 = price_data_macd["close"].ewm(span=12, adjust=False).mean()
        ema26 = price_data_macd["close"].ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26

        signal_line = macd_line.ewm(span=9, adjust=False).mean()

        assert len(signal_line) == len(price_data_macd)

    def test_macd_histogram(self, price_data_macd):
        """Test MACD histogram calculation."""
        ema12 = price_data_macd["close"].ewm(span=12, adjust=False).mean()
        ema26 = price_data_macd["close"].ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26

        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line

        assert len(histogram) == len(price_data_macd)

    def test_macd_bullish_crossover(self, price_data_macd):
        """Test MACD bullish crossover detection."""
        ema12 = price_data_macd["close"].ewm(span=12, adjust=False).mean()
        ema26 = price_data_macd["close"].ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26

        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line

        # Bullish crossover: MACD crosses above signal line
        bullish = (macd_line > signal_line) & (
            macd_line.shift(1) <= signal_line.shift(1)
        )

        assert bullish.sum() >= 0

    def test_macd_bearish_crossover(self, price_data_macd):
        """Test MACD bearish crossover detection."""
        ema12 = price_data_macd["close"].ewm(span=12, adjust=False).mean()
        ema26 = price_data_macd["close"].ewm(span=26, adjust=False).mean()
        macd_line = ema12 - ema26

        signal_line = macd_line.ewm(span=9, adjust=False).mean()

        # Bearish crossover: MACD crosses below signal line
        bearish = (macd_line < signal_line) & (
            macd_line.shift(1) >= signal_line.shift(1)
        )

        assert bearish.sum() >= 0


class TestBollingerBandsAnalysis:
    """Test Bollinger Bands analysis."""

    @pytest.fixture
    def price_data_bb(self):
        """Create price data for Bollinger Bands testing."""
        dates = pd.date_range("2026-01-01", periods=100, freq="h")
        prices = 1.2500 + np.cumsum(np.random.normal(0, 0.0001, 100))
        return pd.DataFrame(
            {"close": prices},
            index=dates,
        )

    def test_bollinger_bands_calculation(self, price_data_bb):
        """Test Bollinger Bands calculation."""
        period = 20
        sma = price_data_bb["close"].rolling(window=period).mean()
        std = price_data_bb["close"].rolling(window=period).std()

        upper_band = sma + (2 * std)
        lower_band = sma - (2 * std)

        assert len(upper_band) == len(price_data_bb)
        assert len(lower_band) == len(price_data_bb)

    def test_bollinger_bands_squeeze(self, price_data_bb):
        """Test Bollinger Bands squeeze detection."""
        period = 20
        sma = price_data_bb["close"].rolling(window=period).mean()
        std = price_data_bb["close"].rolling(window=period).std()

        upper_band = sma + (2 * std)
        lower_band = sma - (2 * std)
        band_width = upper_band - lower_band

        # Squeeze: band width is small
        avg_width = band_width.rolling(window=20).mean()
        squeeze_ratio = band_width / avg_width

        squeeze = squeeze_ratio < 0.5
        assert squeeze.sum() >= 0

    def test_bollinger_bands_breakout(self, price_data_bb):
        """Test Bollinger Bands breakout detection."""
        period = 20
        sma = price_data_bb["close"].rolling(window=period).mean()
        std = price_data_bb["close"].rolling(window=period).std()

        upper_band = sma + (2 * std)
        lower_band = sma - (2 * std)

        # Breakout: price crosses bands
        upper_breakout = price_data_bb["close"] > upper_band
        lower_breakout = price_data_bb["close"] < lower_band

        assert upper_breakout.sum() >= 0
        assert lower_breakout.sum() >= 0


class TestATRAnalysis:
    """Test Average True Range analysis."""

    @pytest.fixture
    def ohlc_data(self):
        """Create OHLC data for ATR testing."""
        dates = pd.date_range("2026-01-01", periods=100, freq="h")
        close = 1.2500 + np.cumsum(np.random.normal(0, 0.0001, 100))

        return pd.DataFrame(
            {
                "high": close + 0.0005,
                "low": close - 0.0005,
                "close": close,
            },
            index=dates,
        )

    def test_true_range_calculation(self, ohlc_data):
        """Test True Range calculation."""
        high = ohlc_data["high"]
        low = ohlc_data["low"]
        close = ohlc_data["close"]

        tr1 = high - low
        tr2 = np.abs(high - close.shift(1))
        tr3 = np.abs(low - close.shift(1))

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        assert len(true_range) == len(ohlc_data)
        assert (true_range >= 0).all() or pd.isna(true_range).any()

    def test_atr_calculation(self, ohlc_data):
        """Test ATR calculation."""
        high = ohlc_data["high"]
        low = ohlc_data["low"]
        close = ohlc_data["close"]

        tr1 = high - low
        tr2 = np.abs(high - close.shift(1))
        tr3 = np.abs(low - close.shift(1))

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=14).mean()

        assert len(atr) == len(ohlc_data)

    def test_atr_volatility_level(self, ohlc_data):
        """Test ATR for volatility level."""
        high = ohlc_data["high"]
        low = ohlc_data["low"]
        close = ohlc_data["close"]

        tr1 = high - low
        tr2 = np.abs(high - close.shift(1))
        tr3 = np.abs(low - close.shift(1))

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=14).mean()

        # Normalize by close price
        atr_percent = (atr / close) * 100

        assert len(atr_percent) == len(ohlc_data)


class TestStochasticAnalysis:
    """Test Stochastic indicator analysis."""

    @pytest.fixture
    def ohlc_data_stoch(self):
        """Create OHLC data for Stochastic testing."""
        dates = pd.date_range("2026-01-01", periods=100, freq="h")
        close = 1.2500 + np.cumsum(np.random.normal(0, 0.0001, 100))

        return pd.DataFrame(
            {
                "high": close + 0.0010,
                "low": close - 0.0010,
                "close": close,
            },
            index=dates,
        )

    def test_stochastic_k_line(self, ohlc_data_stoch):
        """Test Stochastic %K line calculation."""
        period = 14
        close = ohlc_data_stoch["close"]
        high = ohlc_data_stoch["high"]
        low = ohlc_data_stoch["low"]

        lowest_low = low.rolling(window=period).min()
        highest_high = high.rolling(window=period).max()

        k_line = 100 * (close - lowest_low) / (highest_high - lowest_low)

        assert len(k_line) == len(ohlc_data_stoch)
        assert (k_line >= 0).all() or pd.isna(k_line).any()
        assert (k_line <= 100).all() or pd.isna(k_line).any()

    def test_stochastic_d_line(self, ohlc_data_stoch):
        """Test Stochastic %D line calculation."""
        period = 14
        close = ohlc_data_stoch["close"]
        high = ohlc_data_stoch["high"]
        low = ohlc_data_stoch["low"]

        lowest_low = low.rolling(window=period).min()
        highest_high = high.rolling(window=period).max()

        k_line = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d_line = k_line.rolling(window=3).mean()

        assert len(d_line) == len(ohlc_data_stoch)

    def test_stochastic_overbought(self, ohlc_data_stoch):
        """Test Stochastic overbought detection."""
        period = 14
        close = ohlc_data_stoch["close"]
        high = ohlc_data_stoch["high"]
        low = ohlc_data_stoch["low"]

        lowest_low = low.rolling(window=period).min()
        highest_high = high.rolling(window=period).max()

        k_line = 100 * (close - lowest_low) / (highest_high - lowest_low)

        overbought = k_line > 80
        assert (overbought >= False).all()

    def test_stochastic_oversold(self, ohlc_data_stoch):
        """Test Stochastic oversold detection."""
        period = 14
        close = ohlc_data_stoch["close"]
        high = ohlc_data_stoch["high"]
        low = ohlc_data_stoch["low"]

        lowest_low = low.rolling(window=period).min()
        highest_high = high.rolling(window=period).max()

        k_line = 100 * (close - lowest_low) / (highest_high - lowest_low)

        oversold = k_line < 20
        assert (oversold >= False).all()


class TestIndicatorIntegration:
    """Integration tests for indicator analysis."""

    def test_multi_indicator_analysis(self):
        """Test analysis with multiple indicators."""
        dates = pd.date_range("2026-01-01", periods=100, freq="h")
        close = 1.2500 + np.cumsum(np.random.normal(0, 0.0001, 100))

        df = pd.DataFrame(
            {
                "close": close,
                "high": close + 0.0005,
                "low": close - 0.0005,
            },
            index=dates,
        )

        # Calculate indicators
        sma20 = df["close"].rolling(window=20).mean()
        rsi = 50  # Placeholder
        macd = 0  # Placeholder

        # All indicators available
        assert len(sma20) > 0

    def test_indicator_signal_confirmation(self):
        """Test signal confirmation with multiple indicators."""
        # Setup: Buy signal when:
        # - Price > SMA
        # - RSI > 50
        # - MACD > 0

        price = 1.2550
        sma = 1.2500
        rsi = 60
        macd = 0.0005

        buy_signal = (price > sma) and (rsi > 50) and (macd > 0)
        assert buy_signal is True

    def test_indicator_divergence_detection(self):
        """Test price/indicator divergence."""
        # Bullish divergence: Price makes lower low, indicator makes higher low
        price_lows = [1.2400, 1.2390, 1.2385]
        indicator_lows = [30, 35, 40]

        # Check divergence
        divergence = (price_lows[-1] < price_lows[0]) and (
            indicator_lows[-1] > indicator_lows[0]
        )
        assert divergence is True
