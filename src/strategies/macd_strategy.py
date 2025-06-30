# src/strategies/macd_strategy.py
from .base_strategy import BaseStrategy
from backtesting.lib import crossover
import ta
import numpy as np
import logging

# Define crossunder as a helper function
def crossunder(x, y):
    """Return True if x crosses under y (i.e., y crosses over x)."""
    return crossover(y, x)

class MACDStrategy(BaseStrategy):
    """MACD-based trading strategy."""
    def __init__(self, broker, data, params=None, config=None):
        super().__init__(broker, data, params=params, config=config)

    def init(self):
        self.macd = self.I(
            ta.trend.MACD,
            close=self.data.Close,
            window_fast=self.params.get('fast_period', 12),
            window_slow=self.params.get('slow_period', 26),
            window_sign=self.params.get('signal_period', 9)
        ).macd()
        self.signal = self.I(
            ta.trend.MACD,
            close=self.data.Close,
            window_fast=self.params.get('fast_period', 12),
            window_slow=self.params.get('slow_period', 26),
            window_sign=self.params.get('signal_period', 9)
        ).macd_signal()

    def next(self):
        if np.isnan(self.macd[-1]) or np.isnan(self.signal[-1]):
            self._logger.warning("Skipping signal due to invalid MACD value")
            return
        try:
            if crossover(self.macd, self.signal):
                self.buy(size=self.lot_size)
            elif crossunder(self.macd, self.signal):
                self.sell(size=self.lot_size)
            self._logger.debug(
                f"Signal checked: MACD={self.macd[-1]:.2f}, Signal={self.signal[-1]:.2f}, Lot Size={self.lot_size:.6f}"
            )
        except Exception as e:
            self._logger.error(f"Trade execution failed: {e}")