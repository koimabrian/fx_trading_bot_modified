# fx_trading_bot/src/strategies/rsi_strategy.py
# Purpose: Implements RSI-based trading strategy
# pylint: disable=no-member
import pandas as pd
import ta
from backtesting import Strategy

from src.core.base_strategy import BaseStrategy


class RSIStrategy(BaseStrategy):
    """RSI (Relative Strength Index) based trading strategy."""

    def __init__(self, params, db, config, mode="live"):
        """Initialize RSI strategy with parameters.

        Args:
            params: Strategy parameters (period, overbought, oversold, volume)
            db: Database manager instance
            config: Configuration dictionary
            mode: Trading mode ('live' or 'backtest')
        """
        super().__init__(params, db, config, mode)
        self.period = params.get("period", 14)
        self.overbought = params.get("overbought", 70)
        self.oversold = params.get("oversold", 30)
        self.backtest_strategy = self.BacktestRSIStrategy
        self.rsi_cache = {}  # Cache for RSI values

    def generate_entry_signal(self, symbol=None):
        """Generate entry signal based on RSI.

        Requires self.period + 5 rows minimum for accurate calculation.
        """
        # RSI needs period + buffer rows (14 + 5 = 19 rows minimum)
        required = self.period + 5
        data = self.fetch_data(symbol, required_rows=required)
        if data.empty or len(data) < self.period + 1:
            self.logger.warning(
                "Insufficient data for RSI %s: got %d rows, need %d",
                symbol or self.symbol,
                len(data),
                required,
            )
            return None

        data["rsi"] = ta.momentum.RSIIndicator(data["close"], window=self.period).rsi()
        latest = data.iloc[-1]
        prev = data.iloc[-2] if len(data) > 1 else None

        if prev is None:
            return None

        signal = {
            "symbol": symbol or self.symbol,
            "volume": self.volume,
            "timeframe": self.timeframe,
        }

        if latest["rsi"] < self.oversold and prev["rsi"] >= self.oversold:
            signal["action"] = "buy"
            self.logger.debug(
                "Buy signal generated for %s: RSI=%.2f", signal["symbol"], latest["rsi"]
            )
            return signal
        elif latest["rsi"] > self.overbought and prev["rsi"] <= self.overbought:
            signal["action"] = "sell"
            self.logger.debug(
                "Sell signal generated for %s: RSI=%.2f",
                signal["symbol"],
                latest["rsi"],
            )
            return signal
        return None

    def generate_exit_signal(self, position):
        """Generate exit signal based on RSI"""
        data = self.fetch_data(position.symbol)
        if data.empty:
            self.logger.warning("No data available for %s", position.symbol)
            return False

        data["rsi"] = ta.momentum.RSIIndicator(data["close"], window=self.period).rsi()
        latest = data.iloc[-1]

        if position.type == 0:  # Buy position
            if latest["rsi"] > self.overbought:
                self.logger.debug(
                    "Exit buy signal for %s: RSI=%.2f", position.symbol, latest["rsi"]
                )
                return True
        else:  # Sell position
            if latest["rsi"] < self.oversold:
                self.logger.debug(
                    "Exit sell signal for %s: RSI=%.2f", position.symbol, latest["rsi"]
                )
                return True
        return False

    class BacktestRSIStrategy(Strategy):  # pylint: disable=too-few-public-methods
        params = dict(period=14, overbought=70, oversold=30, volume=0.01)
        rsi = None  # type: ignore

        def init(self):
            """Initialize RSI indicator for backtesting."""
            period = self.params["period"]
            self.rsi = self.I(
                lambda x: ta.momentum.RSIIndicator(pd.Series(x), window=period).rsi(),
                self.data.Close,
            )

        def next(self):
            """Generate buy/sell signals based on RSI crossovers."""
            overbought = self.params["overbought"]
            oversold = self.params["oversold"]
            volume = self.params["volume"]
            if self.rsi[-1] < oversold and self.rsi[-2] >= oversold:
                self.buy(size=volume)
            elif self.rsi[-1] > overbought and self.rsi[-2] <= overbought:
                self.sell(size=volume)
