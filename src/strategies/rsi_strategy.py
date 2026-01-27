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
        """Generate entry signal based on RSI with improved detection.

        Uses momentum divergence + RSI levels for more reliable signals.
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

        # Calculate RSI momentum (change in RSI)
        data["rsi_change"] = data["rsi"].diff()

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
        if not self.validate_indicator(latest["rsi"]):
            return None

        signal = {
            "symbol": symbol or self.symbol,
            "volume": self.volume,
            "timeframe": self.timeframe,
        }

        # ===== BUY SIGNALS (IMPROVED) =====
        # Signal 1: RSI oversold with upward momentum (stronger)
        if (
            latest["rsi"] < self.oversold
            and latest["rsi_change"] > 0
            and prev["rsi_change"] < 0
        ):
            signal["action"] = "buy"
            signal["reason"] = f"RSI bounce from oversold ({latest['rsi']:.1f})"
            self.logger.debug(
                "BUY signal for %s: RSI bounce from oversold=%.2f, ATR%%=%.2f",
                signal["symbol"],
                latest["rsi"],
                latest["atr_pct"],
            )
            return signal

        # Signal 2: RSI below 40 with strong upward momentum
        if latest["rsi"] < 40 and latest["rsi_change"] > 5 and latest["atr_pct"] > 0.5:
            signal["action"] = "buy"
            signal["reason"] = f"RSI momentum upward ({latest['rsi']:.1f})"
            self.logger.debug(
                "BUY signal for %s: RSI momentum, RSI=%.2f, ATR%%=%.2f",
                signal["symbol"],
                latest["rsi"],
                latest["atr_pct"],
            )
            return signal

        # ===== SELL SIGNALS (IMPROVED) =====
        # Signal 1: RSI overbought with downward momentum (stronger)
        if (
            latest["rsi"] > self.overbought
            and latest["rsi_change"] < 0
            and prev["rsi_change"] > 0
        ):
            signal["action"] = "sell"
            signal["reason"] = f"RSI pullback from overbought ({latest['rsi']:.1f})"
            self.logger.debug(
                "SELL signal for %s: RSI pullback from overbought=%.2f, ATR%%=%.2f",
                signal["symbol"],
                latest["rsi"],
                latest["atr_pct"],
            )
            return signal

        # Signal 2: RSI above 60 with strong downward momentum
        if latest["rsi"] > 60 and latest["rsi_change"] < -5 and latest["atr_pct"] > 0.5:
            signal["action"] = "sell"
            signal["reason"] = f"RSI momentum downward ({latest['rsi']:.1f})"
            self.logger.debug(
                "SELL signal for %s: RSI momentum down, RSI=%.2f, ATR%%=%.2f",
                signal["symbol"],
                latest["rsi"],
                latest["atr_pct"],
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
        """RSI Strategy for backtesting.py framework."""

        # Define parameters as class attributes - REQUIRED by backtesting.py
        # backtesting.py validates params using hasattr(), so each parameter
        # must be defined as an individual class attribute, not in a params dict
        period = 14
        overbought = 70
        oversold = 30
        volume = 0.01
        rsi = None  # type: ignore

        def init(self):
            """Initialize RSI indicator for backtesting."""
            self.rsi = self.I(
                lambda x: ta.momentum.RSIIndicator(
                    pd.Series(x), window=self.period
                ).rsi(),
                self.data.Close,
            )

        def next(self):
            """Generate buy/sell signals based on RSI crossovers."""
            if self.rsi[-1] < self.oversold and self.rsi[-2] >= self.oversold:
                self.buy(size=self.volume)
            elif self.rsi[-1] > self.overbought and self.rsi[-2] <= self.overbought:
                self.sell(size=self.volume)
