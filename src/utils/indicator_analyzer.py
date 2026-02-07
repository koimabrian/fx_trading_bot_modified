"""
Real-time indicator analysis and signal tracking.

Collects technical indicators (MACD, RSI, SMA, EMA) and signal metrics
for live display on the dashboard.
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.core.data_fetcher import DataFetcher
from src.database.db_manager import DatabaseManager


class IndicatorAnalyzer:
    """Analyzes technical indicators for live signal display."""

    def __init__(self, db: DatabaseManager, mt5_conn=None, config=None):
        """Initialize indicator analyzer.

        Args:
            db: DatabaseManager instance
            mt5_conn: MT5 connector instance (optional, can be None for read-only operations)
            config: Configuration dictionary (optional)
        """
        self.db = db
        self.mt5_conn = mt5_conn
        self.config = config or {}
        self.data_fetcher = DataFetcher(mt5_conn, db, self.config)
        from src.utils.logging_factory import LoggingFactory
        self.logger = LoggingFactory.get_logger(__name__)

    def calculate_rsi(self, prices: np.ndarray, period: int = 14) -> Tuple[float, Dict]:
        """Calculate RSI indicator and signal.

        Args:
            prices: Array of prices
            period: RSI period (default 14)

        Returns:
            Tuple of (rsi_value, {signal_data})
        """
        if len(prices) < period + 1:
            return None, {"status": "insufficient_data"}

        deltas = np.diff(prices)
        gains = deltas.copy()
        losses = -deltas.copy()

        gains[gains < 0] = 0
        losses[losses < 0] = 0

        avg_gain = gains[-period:].mean()
        avg_loss = losses[-period:].mean()

        if avg_loss == 0:
            rs = 0
        else:
            rs = avg_gain / avg_loss

        rsi = 100 - (100 / (1 + rs))

        # Determine signal
        signal = "neutral"
        if rsi < 30:
            signal = "oversold"
        elif rsi > 70:
            signal = "overbought"
        elif rsi < 50:
            signal = "bearish"
        elif rsi > 50:
            signal = "bullish"

        return float(rsi), {
            "value": float(rsi),
            "signal": signal,
            "oversold": bool(rsi < 30),
            "overbought": bool(rsi > 70),
            "period": period,
        }

    def calculate_macd(
        self, prices: np.ndarray, fast: int = 12, slow: int = 26, signal_period: int = 9
    ) -> Tuple[Dict, Dict]:
        """Calculate MACD indicator and signal.

        Args:
            prices: Array of prices
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal_period: Signal line period (default 9)

        Returns:
            Tuple of (macd_line, {signal_data})
        """
        if len(prices) < slow + signal_period:
            return None, {"status": "insufficient_data"}

        ema_fast = self._calculate_ema(prices, fast)
        ema_slow = self._calculate_ema(prices, slow)

        macd_line = ema_fast - ema_slow
        macd_signal = self._calculate_ema(macd_line, signal_period)
        histogram = macd_line - macd_signal

        # Determine signal
        signal = "neutral"
        if histogram[-1] > 0 and histogram[-2] <= 0:
            signal = "bullish_crossover"
        elif histogram[-1] < 0 and histogram[-2] >= 0:
            signal = "bearish_crossover"
        elif histogram[-1] > 0:
            signal = "bullish"
        elif histogram[-1] < 0:
            signal = "bearish"

        return macd_line[-1], {
            "macd": float(macd_line[-1]),
            "signal_line": float(macd_signal[-1]),
            "histogram": float(histogram[-1]),
            "signal": signal,
            "is_bullish": bool(histogram[-1] > 0),
            "crossover_pending": bool(abs(histogram[-1]) < abs(histogram[-2])),
        }

    def calculate_moving_averages(
        self, prices: np.ndarray, periods: List[int] = [20, 50, 200]
    ) -> Dict:
        """Calculate SMA and EMA indicators.

        Args:
            prices: Array of prices
            periods: List of periods to calculate

        Returns:
            Dictionary with SMA and EMA values
        """
        if len(prices) == 0:
            return {"status": "insufficient_data"}

        result = {"sma": {}, "ema": {}}

        for period in periods:
            if len(prices) >= period:
                sma = np.mean(prices[-period:])
                ema = self._calculate_ema(prices, period)[-1]

                result["sma"][f"sma_{period}"] = float(sma)
                result["ema"][f"ema_{period}"] = float(ema)

        # Determine trend signal
        if result["sma"] and result["ema"]:
            current_price = prices[-1]
            sma_20 = result["sma"].get("sma_20")
            sma_50 = result["sma"].get("sma_50")
            sma_200 = result["sma"].get("sma_200")

            trend = "neutral"
            if current_price > sma_20 > sma_50 > sma_200:
                trend = "strong_uptrend"
            elif current_price > sma_50 > sma_200:
                trend = "uptrend"
            elif current_price < sma_20 < sma_50 < sma_200:
                trend = "strong_downtrend"
            elif current_price < sma_50 < sma_200:
                trend = "downtrend"

            result["trend"] = trend
            result["current_price"] = float(current_price)

        return result

    def calculate_volatility(self, prices: np.ndarray, period: int = 14) -> Dict:
        """Calculate ATR and volatility metrics.

        Args:
            prices: Array of prices (high, low, close data needed ideally)
            period: ATR period (default 14)

        Returns:
            Dictionary with volatility metrics
        """
        if len(prices) < period:
            return {"status": "insufficient_data"}

        # Calculate simple volatility as standard deviation
        returns = np.diff(np.log(prices))
        volatility = np.std(returns[-period:])

        # Volatility level classification
        vol_level = "low"
        if volatility > 0.02:
            vol_level = "high"
        elif volatility > 0.01:
            vol_level = "medium"

        return {
            "volatility": float(volatility),
            "volatility_pct": float(volatility * 100),
            "level": vol_level,
            "period": period,
            "std_dev": float(np.std(prices[-period:])),
        }

    def get_all_indicators(self, symbol: str, timeframe: str = "M15") -> Dict:
        """Get all indicators for a symbol.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe string (M15, H1, H4, etc.)

        Returns:
            Dictionary with all indicator values and signals
        """
        try:
            # Fetch recent data
            tf_minutes = self._parse_timeframe(timeframe)
            df = self.data_fetcher.fetch_data(
                symbol=symbol, timeframe=timeframe, limit=500
            )

            if df is None or len(df) == 0:
                return {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "status": "no_data",
                    "message": "No market data available",
                }

            prices = df["close"].values
            high = df["high"].values if "high" in df.columns else prices
            low = df["low"].values if "low" in df.columns else prices

            # Calculate all indicators
            indicators = {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": pd.Timestamp.now().isoformat(),
                "price": {
                    "current": float(prices[-1]),
                    "change": float(prices[-1] - prices[-2]) if len(prices) > 1 else 0,
                    "change_pct": float(
                        ((prices[-1] - prices[-2]) / prices[-2] * 100)
                        if len(prices) > 1 and prices[-2] != 0
                        else 0
                    ),
                },
            }

            # RSI
            rsi_val, rsi_signal = self.calculate_rsi(prices)
            if rsi_val is not None:
                indicators["rsi"] = rsi_signal

            # MACD
            macd_val, macd_signal = self.calculate_macd(prices)
            if macd_val is not None:
                indicators["macd"] = macd_signal

            # Moving Averages
            ma_data = self.calculate_moving_averages(prices)
            if "status" not in ma_data:
                indicators["moving_averages"] = ma_data

            # Volatility
            vol_data = self.calculate_volatility(prices)
            if "status" not in vol_data:
                indicators["volatility"] = vol_data

            return indicators

        except Exception as e:
            self.logger.error(f"Error calculating indicators for {symbol}: {e}")
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "status": "error",
                "message": str(e),
            }

    def get_entry_signal_checks(self, symbol: str, timeframe: str = "M15") -> Dict:
        """Get detailed entry signal check results.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe string

        Returns:
            Dictionary with all signal checks and their results
        """
        indicators = self.get_all_indicators(symbol, timeframe)

        if "status" in indicators:
            return indicators

        checks = {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": indicators.get("timestamp"),
            "checks": {},
            "overall_signal": "neutral",
        }

        # RSI checks
        if "rsi" in indicators:
            rsi = indicators["rsi"]
            checks["checks"]["rsi"] = {
                "value": rsi["value"],
                "signal": rsi["signal"],
                "checks": {
                    "oversold": {"passed": rsi["oversold"], "description": "RSI < 30"},
                    "overbought": {
                        "passed": rsi["overbought"],
                        "description": "RSI > 70",
                    },
                    "bullish": {"passed": rsi["value"] > 50, "description": "RSI > 50"},
                    "bearish": {"passed": rsi["value"] < 50, "description": "RSI < 50"},
                },
            }

        # MACD checks
        if "macd" in indicators:
            macd = indicators["macd"]
            checks["checks"]["macd"] = {
                "macd": macd["macd"],
                "signal_line": macd["signal_line"],
                "histogram": macd["histogram"],
                "signal": macd["signal"],
                "checks": {
                    "bullish_crossover": {
                        "passed": macd["signal"] == "bullish_crossover",
                        "description": "MACD above signal line",
                    },
                    "bearish_crossover": {
                        "passed": macd["signal"] == "bearish_crossover",
                        "description": "MACD below signal line",
                    },
                    "bullish": {
                        "passed": macd["is_bullish"],
                        "description": "Histogram positive",
                    },
                },
            }

        # Moving Average checks
        if "moving_averages" in indicators:
            ma = indicators["moving_averages"]
            checks["checks"]["moving_averages"] = {
                "trend": ma.get("trend", "neutral"),
                "current_price": ma.get("current_price"),
                "sma": ma.get("sma", {}),
                "ema": ma.get("ema", {}),
                "checks": {
                    "price_above_sma20": {
                        "passed": (
                            ma.get("current_price", 0)
                            > ma.get("sma", {}).get("sma_20", 0)
                        ),
                        "description": "Price > SMA20",
                    },
                    "sma20_above_50": {
                        "passed": (
                            ma.get("sma", {}).get("sma_20", 0)
                            > ma.get("sma", {}).get("sma_50", 0)
                        ),
                        "description": "SMA20 > SMA50",
                    },
                    "uptrend": {
                        "passed": "uptrend" in ma.get("trend", ""),
                        "description": "In uptrend",
                    },
                },
            }

        # Volatility checks
        if "volatility" in indicators:
            vol = indicators["volatility"]
            checks["checks"]["volatility"] = {
                "volatility": vol["volatility"],
                "volatility_pct": vol["volatility_pct"],
                "level": vol["level"],
                "checks": {
                    "sufficient_vol": {
                        "passed": vol["level"] in ["medium", "high"],
                        "description": "Volatility > minimum",
                    },
                    "low_vol": {
                        "passed": vol["level"] == "low",
                        "description": "Low volatility period",
                    },
                },
            }

        # Calculate overall signal
        all_passed = [
            c.get("passed", False)
            for check_group in checks["checks"].values()
            if isinstance(check_group, dict) and "checks" in check_group
            for c in check_group["checks"].values()
        ]

        if all_passed:
            passed_count = sum(all_passed)
            total_count = len(all_passed)
            if passed_count >= total_count * 0.7:
                checks["overall_signal"] = "strong_buy"
            elif passed_count >= total_count * 0.5:
                checks["overall_signal"] = "buy"

        checks["signal_strength"] = len([c for c in all_passed if c]) / max(
            len(all_passed), 1
        )

        return checks

    @staticmethod
    def _calculate_ema(prices: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average.

        Args:
            prices: Array of prices
            period: EMA period

        Returns:
            EMA values
        """
        if len(prices) < period:
            return np.array([])

        multiplier = 2 / (period + 1)
        ema = np.zeros_like(prices, dtype=float)
        ema[period - 1] = np.mean(prices[:period])

        for i in range(period, len(prices)):
            ema[i] = (prices[i] * multiplier) + (ema[i - 1] * (1 - multiplier))

        return ema

    @staticmethod
    def _parse_timeframe(timeframe: str) -> int:
        """Parse timeframe string to minutes.

        Args:
            timeframe: Timeframe string (M15, H1, H4, D1, etc.)

        Returns:
            Minutes as integer
        """
        timeframe = timeframe.upper()
        if timeframe.startswith("M"):
            return int(timeframe[1:])
        elif timeframe.startswith("H"):
            return int(timeframe[1:]) * 60
        elif timeframe.startswith("D"):
            return int(timeframe[1:]) * 1440
        else:
            return 15  # Default to M15
