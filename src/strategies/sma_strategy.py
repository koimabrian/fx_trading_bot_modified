# fx_trading_bot/src/strategies/sma_strategy.py
# Purpose: Implements SMA Crossover trading strategy
# pylint: disable=no-member
import pandas as pd
import ta
from backtesting import Strategy

from src.core.base_strategy import BaseStrategy


class SMAStrategy(BaseStrategy):
    """Simple Moving Average (SMA) Crossover trading strategy."""

    def __init__(self, params, db, config, mode="live"):
        """Initialize SMA strategy with parameters.

        Args:
            params: Strategy parameters (fast_period, slow_period, volume)
            db: Database manager instance
            config: Configuration dictionary
            mode: Trading mode ('live' or 'backtest')
        """
        super().__init__(params, db, config, mode)
        self.fast_period = params.get("fast_period", 10)
        self.slow_period = params.get("slow_period", 20)
        self.backtest_strategy = self.BacktestSMAStrategy
        self.sma_cache = {}  # Cache for SMA values

    def generate_entry_signal(self, symbol=None):
        """Generate entry signal based on SMA crossover.

        Trades on crossover: fast SMA crosses above/below slow SMA.
        Requires slow_period + buffer rows for accurate calculation.
        """
        # SMA needs slow_period + buffer rows
        required = self.slow_period + 5
        data = self.fetch_data(symbol, required_rows=required)
        if data.empty or len(data) < self.slow_period + 1:
            self.logger.warning(
                "Insufficient data for SMA %s: got %d rows, need %d",
                symbol or self.symbol,
                len(data),
                required,
            )
            return None

        # Calculate SMAs
        data["sma_fast"] = ta.trend.SMAIndicator(
            data["close"], window=self.fast_period
        ).sma_indicator()
        data["sma_slow"] = ta.trend.SMAIndicator(
            data["close"], window=self.slow_period
        ).sma_indicator()

        # Calculate SMA crossover (fast - slow)
        data["sma_diff"] = data["sma_fast"] - data["sma_slow"]
        data["sma_diff_prev"] = data["sma_diff"].shift(1)

        # Calculate ATR for volatility (14-period standard)
        atr = ta.volatility.AverageTrueRange(
            data["high"], data["low"], data["close"], window=14
        )
        data["atr"] = atr.average_true_range()
        data["atr_pct"] = (data["atr"] / data["close"]) * 100

        latest = data.iloc[-1]
        prev = data.iloc[-2] if len(data) > 1 else None

        if prev is None:
            return None

        signal = {
            "symbol": symbol or self.symbol,
            "volume": self.volume,
            "timeframe": self.timeframe,
        }

        # ===== BUY SIGNAL =====
        # Fast SMA crosses above Slow SMA (golden cross)
        if prev["sma_diff"] <= 0 and latest["sma_diff"] > 0:
            signal["action"] = "buy"
            signal["reason"] = "SMA Golden Cross (SMA10 > SMA20)"
            signal["confidence"] = 0.7
            self.logger.info(
                "BUY Signal: %s - SMA Crossover (Fast: %.4f > Slow: %.4f)",
                symbol or self.symbol,
                latest["sma_fast"],
                latest["sma_slow"],
            )
            return signal

        # ===== SELL SIGNAL =====
        # Fast SMA crosses below Slow SMA (death cross)
        if prev["sma_diff"] >= 0 and latest["sma_diff"] < 0:
            signal["action"] = "sell"
            signal["reason"] = "SMA Death Cross (SMA10 < SMA20)"
            signal["confidence"] = 0.7
            self.logger.info(
                "SELL Signal: %s - SMA Crossover (Fast: %.4f < Slow: %.4f)",
                symbol or self.symbol,
                latest["sma_fast"],
                latest["sma_slow"],
            )
            return signal

        return None

    def generate_exit_signal(self, symbol=None, entry_price=None):
        """Generate exit signal based on SMA trend reversal or price targets.

        Uses SMA for trend confirmation and ATR for risk management.
        """
        if entry_price is None:
            return None

        data = self.fetch_data(symbol, required_rows=self.slow_period + 10)
        if data.empty or len(data) < self.slow_period:
            return None

        # Calculate SMAs
        data["sma_fast"] = ta.trend.SMAIndicator(
            data["close"], window=self.fast_period
        ).sma_indicator()
        data["sma_slow"] = ta.trend.SMAIndicator(
            data["close"], window=self.slow_period
        ).sma_indicator()

        # Calculate ATR for stops
        atr = ta.volatility.AverageTrueRange(
            data["high"], data["low"], data["close"], window=14
        )
        data["atr"] = atr.average_true_range()

        latest = data.iloc[-1]
        current_price = latest["close"]

        # Risk management: Exit if price falls below entry - 2*ATR
        atr_stop = entry_price - (2 * latest["atr"])
        if current_price < atr_stop:
            return {
                "action": "close",
                "reason": "ATR Stop Loss",
                "stop_price": atr_stop,
            }

        # Trend reversal: Exit if SMA trend reverses
        if current_price < latest["sma_slow"]:
            return {
                "action": "close",
                "reason": "Price below SMA20",
                "stop_price": latest["sma_slow"],
            }

        return None

    class BacktestSMAStrategy(Strategy):
        """Backtesting strategy for SMA Crossover."""

        fast_period = 10
        slow_period = 20
        volume = 0.01

        def init(self):
            """Initialize indicators."""
            self.sma_fast = self.I(
                lambda x: pd.Series(x).rolling(self.fast_period).mean(),
                self.data.Close,
            )
            self.sma_slow = self.I(
                lambda x: pd.Series(x).rolling(self.slow_period).mean(),
                self.data.Close,
            )

        def next(self):
            """Execute strategy logic on each bar."""
            if len(self.data) < self.slow_period + 1:
                return

            # Skip if not enough data
            if pd.isna(self.sma_fast[-1]) or pd.isna(self.sma_slow[-1]):
                return

            # Golden Cross: Buy signal
            if (
                self.sma_fast[-2] <= self.sma_slow[-2]
                and self.sma_fast[-1] > self.sma_slow[-1]
            ):
                if not self.position:
                    self.buy()

            # Death Cross: Sell signal
            if (
                self.sma_fast[-2] >= self.sma_slow[-2]
                and self.sma_fast[-1] < self.sma_slow[-1]
            ):
                if self.position:
                    self.position.close()
