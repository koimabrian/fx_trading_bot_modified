# fx_trading_bot/backtests/strategies/backtest_rsi_strategy.py
# Purpose: RSI strategy adapted for Backtesting.py
from backtesting import Strategy
import ta
import pandas as pd

class BacktestRSIStrategy(Strategy):
    # Strategy parameters
    period = 14
    overbought = 70
    oversold = 30
    size = 0.1  # Trade size in units (ounces for XAUUSDm), reduced to fit margin

    def init(self):
        """Initialize the strategy"""
        # Convert self.data.Close to a pandas Series
        close = pd.Series(self.data.Close, index=self.data.index)
        # Compute RSI indicator
        rsi = ta.momentum.RSIIndicator(close, window=self.period).rsi()
        # Register the RSI indicator with Backtesting.py
        self.rsi = self.I(lambda x: x, rsi)

    def next(self):
        """Define the trading logic for each candle"""
        if len(self.rsi) < 2:
            return

        latest_rsi = self.rsi[-1]
        previous_rsi = self.rsi[-2]

        # Entry signals
        if previous_rsi >= self.oversold and latest_rsi < self.oversold:
            self.buy(size=self.size)
        elif previous_rsi <= self.overbought and latest_rsi > self.overbought:
            self.sell(size=self.size)

        # Exit signals (close positions)
        for trade in self.trades:
            if trade.is_long:
                if previous_rsi <= self.overbought and latest_rsi > self.overbought:
                    trade.close()
            elif trade.is_short:
                if previous_rsi >= self.oversold and latest_rsi < self.oversold:
                    trade.close()