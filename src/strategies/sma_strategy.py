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

        # Use base class ATR calculation
        data = self.calculate_atr(data)

        # Use base class data getter
        latest, prev, prev2 = self.get_latest_data(data)
        if latest is None:
            return None

        # Use base class signal creator
        signal = self.create_base_signal(symbol)

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
            """Initialize SMA indicators for backtesting framework."""
            self.sma_fast = self.I(
                lambda x: pd.Series(x).rolling(self.fast_period).mean(),
                self.data.Close,
            )
            self.sma_slow = self.I(
                lambda x: pd.Series(x).rolling(self.slow_period).mean(),
                self.data.Close,
            )

        def next(self):
            """Execute SMA crossover strategy logic on each price bar."""
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
