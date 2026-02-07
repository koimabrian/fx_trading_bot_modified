# fx_trading_bot/src/strategies/ema_strategy.py
# Purpose: Implements EMA Crossover trading strategy
# pylint: disable=no-member
import pandas as pd
import ta

from backtesting import Strategy
from src.core.base_strategy import BaseStrategy


class EMAStrategy(BaseStrategy):
    """Exponential Moving Average (EMA) Crossover trading strategy."""

    def __init__(self, params, db, config, mode="live"):
        """Initialize EMA strategy with parameters.

        Args:
            params: Strategy parameters (fast_period, slow_period, volume)
            db: Database manager instance
            config: Configuration dictionary
            mode: Trading mode ('live' or 'backtest')
        """
        super().__init__(params, db, config, mode)
        self.fast_period = params.get("fast_period", 10)
        self.slow_period = params.get("slow_period", 20)
        self.backtest_strategy = self.BacktestEMAStrategy
        self.ema_cache = {}  # Cache for EMA values

    def generate_entry_signal(self, symbol=None):
        """Generate entry signal based on EMA crossover.

        Trades on crossover: fast EMA crosses above/below slow EMA.
        EMA responds faster than SMA for more reactive trading.
        Requires slow_period + buffer rows for accurate calculation.

        Args:
            symbol: Trading symbol to analyze. Defaults to instance symbol.

        Returns:
            Signal dictionary with action, reason, confidence, or None if no signal.
        """
        # Fetch data with required rows
        required = self.slow_period + 5
        data = self.fetch_data(symbol, required_rows=required)

        # Use base class validation
        if not self.validate_data(data, self.slow_period):
            return None

        # Calculate EMAs (more responsive than SMA)
        data["ema_fast"] = ta.trend.EMAIndicator(
            data["close"], window=self.fast_period
        ).ema_indicator()
        data["ema_slow"] = ta.trend.EMAIndicator(
            data["close"], window=self.slow_period
        ).ema_indicator()

        # Calculate EMA crossover (fast - slow)
        data["ema_diff"] = data["ema_fast"] - data["ema_slow"]
        data["ema_diff_prev"] = data["ema_diff"].shift(1)

        # Use base class ATR calculation
        data = self.calculate_atr(data)

        # Use base class data getter
        latest, prev, prev2 = self.get_latest_data(data)
        if latest is None:
            return None

        # Use base class signal creator
        signal = self.create_base_signal(symbol)

        # ===== BUY SIGNAL =====
        # Fast EMA crosses above Slow EMA (golden cross)
        if prev["ema_diff"] <= 0 and latest["ema_diff"] > 0:
            signal["action"] = "buy"
            signal["reason"] = "EMA Golden Cross (EMA10 > EMA20)"
            signal["confidence"] = 0.75  # Slightly higher confidence than SMA
            self.logger.info(
                "BUY Signal: %s - EMA Crossover (Fast: %.4f > Slow: %.4f)",
                symbol or self.symbol,
                latest["ema_fast"],
                latest["ema_slow"],
            )
            return signal

        # ===== SELL SIGNAL =====
        # Fast EMA crosses below Slow EMA (death cross)
        if prev["ema_diff"] >= 0 and latest["ema_diff"] < 0:
            signal["action"] = "sell"
            signal["reason"] = "EMA Death Cross (EMA10 < EMA20)"
            signal["confidence"] = 0.75
            self.logger.info(
                "SELL Signal: %s - EMA Crossover (Fast: %.4f < Slow: %.4f)",
                symbol or self.symbol,
                latest["ema_fast"],
                latest["ema_slow"],
            )
            return signal

        return None

    def generate_exit_signal(self, symbol=None, entry_price=None):
        """Generate exit signal based on EMA trend reversal or price targets.

        Uses EMA for trend confirmation and ATR for risk management.
        EMA provides faster exits than SMA.

        Args:
            symbol: Trading symbol to analyze. Defaults to instance symbol.
            entry_price: Original entry price for calculating stop levels.

        Returns:
            Exit signal dictionary with action and reason, or None if no exit.
        """
        if entry_price is None:
            return None

        data = self.fetch_data(symbol, required_rows=self.slow_period + 10)
        if data.empty or len(data) < self.slow_period:
            return None

        # Calculate EMAs
        data["ema_fast"] = ta.trend.EMAIndicator(
            data["close"], window=self.fast_period
        ).ema_indicator()
        data["ema_slow"] = ta.trend.EMAIndicator(
            data["close"], window=self.slow_period
        ).ema_indicator()

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

        # Trend reversal: Exit if EMA trend reverses (faster than SMA)
        if current_price < latest["ema_slow"]:
            return {
                "action": "close",
                "reason": "Price below EMA20",
                "stop_price": latest["ema_slow"],
            }

        return None

    class BacktestEMAStrategy(Strategy):
        """Backtesting strategy for EMA Crossover."""

        fast_period = 10
        slow_period = 20
        volume = 0.01

        def init(self):
            """Initialize EMA indicators for backtesting framework."""
            self.ema_fast = self.I(
                lambda x: pd.Series(x).ewm(span=self.fast_period, adjust=False).mean(),
                self.data.Close,
            )
            self.ema_slow = self.I(
                lambda x: pd.Series(x).ewm(span=self.slow_period, adjust=False).mean(),
                self.data.Close,
            )

        def next(self):
            """Execute EMA crossover strategy logic on each price bar."""
            if len(self.data) < self.slow_period + 1:
                return

            # Skip if not enough data
            if pd.isna(self.ema_fast[-1]) or pd.isna(self.ema_slow[-1]):
                return

            # Golden Cross: Buy signal
            if (
                self.ema_fast[-2] <= self.ema_slow[-2]
                and self.ema_fast[-1] > self.ema_slow[-1]
            ):
                if not self.position:
                    self.buy()

            # Death Cross: Sell signal
            if (
                self.ema_fast[-2] >= self.ema_slow[-2]
                and self.ema_fast[-1] < self.ema_slow[-1]
            ):
                if self.position:
                    self.position.close()
