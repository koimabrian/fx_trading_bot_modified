# fx_trading_bot/src/strategies/macd_strategy.py
# Purpose: Implements MACD-based trading strategy

import pandas as pd
import ta
from backtesting import Strategy

from src.core.base_strategy import BaseStrategy


class MACDStrategy(BaseStrategy):
    """MACD (Moving Average Convergence Divergence) based trading strategy."""

    def __init__(self, params, db, config, mode="live"):
        """Initialize MACD strategy with parameters.

        Args:
            params: Strategy parameters (fast_period, slow_period, signal_period, volume)
            db: Database manager instance
            config: Configuration dictionary
            mode: Trading mode ('live' or 'backtest')
        """
        super().__init__(params, db, config, mode)
        self.fast_period = params.get("fast_period", 12)
        self.slow_period = params.get("slow_period", 26)
        self.signal_period = params.get("signal_period", 9)
        self.backtest_strategy = self.BacktestMACDStrategy

    def generate_entry_signal(self, symbol=None):
        """Generate entry signal based on MACD with improved histogram divergence detection.

        Uses MACD histogram strength + direction for more reliable signals.
        Requires slow_period + signal_period + buffer rows for accuracy.
        """
        # MACD needs slow + signal periods + buffer
        required = self.slow_period + self.signal_period + 5
        data = self.fetch_data(symbol, required_rows=required)
        if data.empty or len(data) < self.slow_period + 1:
            self.logger.warning(
                "Insufficient data for MACD %s: got %d rows, need %d",
                symbol or self.symbol,
                len(data),
                required,
            )
            return None

        macd = ta.trend.MACD(
            data["close"],
            window_fast=self.fast_period,
            window_slow=self.slow_period,
            window_sign=self.signal_period,
        )
        data["macd"] = macd.macd()
        data["macd_signal"] = macd.macd_signal()
        data["macd_hist"] = macd.macd_diff()

        # Calculate MACD histogram momentum (change in histogram)
        data["hist_change"] = data["macd_hist"].diff()

        # Calculate ATR for volatility (14-period standard)
        atr = ta.volatility.AverageTrueRange(
            data["high"], data["low"], data["close"], window=14
        )
        data["atr"] = atr.average_true_range()
        data["atr_pct"] = (data["atr"] / data["close"]) * 100

        latest = data.iloc[-1]
        prev = data.iloc[-2] if len(data) > 1 else None
        prev2 = data.iloc[-3] if len(data) > 2 else None

        if prev is None:
            return None

        # Validate indicator values before using them
        if not self.validate_indicator(latest["macd_hist"]):
            return None

        signal = {
            "symbol": symbol or self.symbol,
            "volume": self.volume,
            "timeframe": self.timeframe,
        }

        # ===== BUY SIGNALS (IMPROVED) =====
        # Signal 1: Histogram crosses above zero (stronger momentum change)
        if (
            latest["macd_hist"] > 0
            and prev["macd_hist"] <= 0
            and latest["atr_pct"] > 0.5
        ):
            signal["action"] = "buy"
            signal["reason"] = f"MACD histogram bullish crossover"
            self.logger.debug(
                "BUY signal for %s: MACD histogram crosses zero (%.4f), ATR%%=%.2f",
                signal["symbol"],
                latest["macd_hist"],
                latest["atr_pct"],
            )
            return signal

        # Signal 2: MACD line crosses above signal line with positive histogram
        if (
            latest["macd"] > latest["macd_signal"]
            and prev["macd"] <= prev["macd_signal"]
            and latest["macd_hist"] > 0
        ):
            signal["action"] = "buy"
            signal["reason"] = f"MACD line bullish crossover (histogram > 0)"
            self.logger.debug(
                "BUY signal for %s: MACD bullish crossover, hist=%.4f, ATR%%=%.2f",
                signal["symbol"],
                latest["macd_hist"],
                latest["atr_pct"],
            )
            return signal

        # Signal 3: Histogram growing (increasing positive divergence)
        if (
            latest["macd_hist"] > 0
            and latest["hist_change"] > 0
            and latest["macd_hist"] > prev["macd_hist"] * 1.5  # 50% increase
            and latest["atr_pct"] > 0.5
        ):
            signal["action"] = "buy"
            signal["reason"] = f"MACD histogram strengthening upward"
            self.logger.debug(
                "BUY signal for %s: MACD histogram accelerating, hist=%.4f, ATR%%=%.2f",
                signal["symbol"],
                latest["macd_hist"],
                latest["atr_pct"],
            )
            return signal

        # ===== SELL SIGNALS (IMPROVED) =====
        # Signal 1: Histogram crosses below zero (stronger momentum change)
        if (
            latest["macd_hist"] < 0
            and prev["macd_hist"] >= 0
            and latest["atr_pct"] > 0.5
        ):
            signal["action"] = "sell"
            signal["reason"] = f"MACD histogram bearish crossover"
            self.logger.debug(
                "SELL signal for %s: MACD histogram crosses zero (%.4f), ATR%%=%.2f",
                signal["symbol"],
                latest["macd_hist"],
                latest["atr_pct"],
            )
            return signal

        # Signal 2: MACD line crosses below signal line with negative histogram
        if (
            latest["macd"] < latest["macd_signal"]
            and prev["macd"] >= prev["macd_signal"]
            and latest["macd_hist"] < 0
        ):
            signal["action"] = "sell"
            signal["reason"] = f"MACD line bearish crossover (histogram < 0)"
            self.logger.debug(
                "SELL signal for %s: MACD bearish crossover, hist=%.4f, ATR%%=%.2f",
                signal["symbol"],
                latest["macd_hist"],
                latest["atr_pct"],
            )
            return signal

        # Signal 3: Histogram shrinking (increasing negative divergence)
        if (
            latest["macd_hist"] < 0
            and latest["hist_change"] < 0
            and latest["macd_hist"]
            < prev["macd_hist"] * 1.5  # 50% increase in negativity
            and latest["atr_pct"] > 0.5
        ):
            signal["action"] = "sell"
            signal["reason"] = f"MACD histogram strengthening downward"
            self.logger.debug(
                "SELL signal for %s: MACD histogram accelerating down, hist=%.4f, ATR%%=%.2f",
                signal["symbol"],
                latest["macd_hist"],
                latest["atr_pct"],
            )
            return signal

        return None

    def generate_exit_signal(self, position):
        """Generate exit signal based on MACD"""
        data = self.fetch_data(position.symbol)
        if data.empty:
            self.logger.warning("No data available for %s", position.symbol)
            return False

        macd = ta.trend.MACD(
            data["close"],
            window_fast=self.fast_period,
            window_slow=self.slow_period,
            window_sign=self.signal_period,
        )
        data["macd"] = macd.macd()
        data["macd_signal"] = macd.macd_signal()
        latest = data.iloc[-1]

        if position.type == 0:  # Buy position
            if latest["macd"] < latest["macd_signal"]:
                self.logger.debug(
                    "Exit buy signal for %s: MACD crossunder", position.symbol
                )
                return True
        else:  # Sell position
            if latest["macd"] > latest["macd_signal"]:
                self.logger.debug(
                    "Exit sell signal for %s: MACD crossover", position.symbol
                )
                return True
        return False

    class BacktestMACDStrategy(Strategy):  # pylint: disable=too-few-public-methods
        """MACD Strategy for backtesting.py framework."""

        # Define parameters as class attributes - REQUIRED by backtesting.py
        # backtesting.py validates params using hasattr(), so each parameter
        # must be defined as an individual class attribute, not in a params dict
        fast_period = 12
        slow_period = 26
        signal_period = 9
        volume = 0.01
        macd = None  # type: ignore
        signal = None  # type: ignore

        def init(self):
            """Initialize MACD indicator for backtesting."""
            macd = ta.trend.MACD(
                pd.Series(self.data.Close),
                window_fast=self.fast_period,
                window_slow=self.slow_period,
                window_sign=self.signal_period,
            )
            self.macd = self.I(macd.macd)
            self.signal = self.I(macd.macd_signal)

        def next(self):
            """Generate buy/sell signals based on MACD crossovers."""
            if self.macd[-1] > self.signal[-1] and self.macd[-2] <= self.signal[-2]:
                self.buy(size=self.volume)
            elif self.macd[-1] < self.signal[-1] and self.macd[-2] >= self.signal[-2]:
                self.sell(size=self.volume)
