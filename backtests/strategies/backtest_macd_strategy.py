# fx_trading_bot/backtests/strategies/backtest_macd_strategy.py
# Purpose: MACD strategy adapted for Backtesting.py
from backtesting import Strategy
import ta
import pandas as pd

class BacktestMACDStrategy(Strategy):
    # Strategy parameters
    fast_period = 12
    slow_period = 26
    signal_period = 9
    size = 0.1  # Trade size in units (ounces for XAUUSDm), reduced to fit margin

    def init(self):
        """Initialize the strategy"""
        # Convert self.data.Close to a pandas Series
        close = pd.Series(self.data.Close, index=self.data.index)
        # Compute MACD indicator
        macd = ta.trend.MACD(close, window_fast=self.fast_period,
                             window_slow=self.slow_period, window_sign=self.signal_period)
        self.macd = self.I(lambda x: x, macd.macd())
        self.signal = self.I(lambda x: x, macd.macd_signal())

    def next(self):
        """Define the trading logic for each candle"""
        if len(self.macd) < 2:
            return

        latest_macd = self.macd[-1]
        latest_signal = self.signal[-1]
        previous_macd = self.macd[-2]
        previous_signal = self.signal[-2]

        # Entry signals
        if previous_macd < previous_signal and latest_macd > latest_signal:
            self.buy(size=self.size)
        elif previous_macd > previous_signal and latest_macd < latest_signal:
            self.sell(size=self.size)

        # Exit signals
        for trade in self.trades:
            if trade.is_long:
                if previous_macd > previous_signal and latest_macd < latest_signal:
                    trade.close()
            elif trade.is_short:
                if previous_macd < previous_signal and latest_macd > latest_signal:
                    trade.close()