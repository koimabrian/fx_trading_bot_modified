# src/strategies/rsi_strategy.py
from .base_strategy import BaseStrategy
from backtesting.lib import crossover
import ta
import numpy as np
import logging

# Define crossunder as a helper function
def crossunder(x, y):
    """Return True if x crosses under y (i.e., y crosses over x)."""
    return crossover(y, x)

class RSIStrategy(BaseStrategy):
    """RSI-based trading strategy."""
    def __init__(self, broker, data, params=None, config=None):
        super().__init__(broker, data, params=params, config=config)

    def init(self):
        self.rsi = self.I(
            ta.momentum.RSIIndicator,
            close=self.data.Close,
            window=self.params.get('period', 14)
        ).rsi()

    def next(self):
        if np.isnan(self.rsi[-1]):
            self._logger.warning("Skipping signal due to invalid RSI value")
            return
        try:
            if crossover(self.rsi, self.params.get('buy_threshold', 15)):
                self.buy(size=self.lot_size)
            elif crossunder(self.rsi, self.params.get('sell_threshold', 85)):
                self.sell(size=self.lot_size)
            self._logger.debug(f"Signal checked: RSI={self.rsi[-1]:.2f}, Lot Size={self.lot_size:.6f}")
        except Exception as e:
            self._logger.error(f"Trade execution failed: {e}")