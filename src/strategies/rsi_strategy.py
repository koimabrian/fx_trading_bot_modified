# src/strategies/rsi_strategy.py
from src.core.base_strategy import BaseStrategy
import ta
import logging
import pandas as pd
import MetaTrader5 as mt5

class RSIStrategy(BaseStrategy):
    """RSI-based trading strategy."""
    def __init__(self, params, db, config, mode='live'):
        super().__init__(params, db, config, mode)
        self.period = params.get('period', 14)
        self.overbought = params.get('overbought', 70)
        self.oversold = params.get('oversold', 30)

    def generate_entry_signal(self, symbol=None):
        """Generate an entry signal based on RSI."""
        data = self.fetch_data(symbol)
        if data.empty:
            self.logger.warning(f"No data available for {symbol or self.symbol}")
            return None
        rsi = ta.momentum.RSIIndicator(close=data['close'], window=self.period).rsi()
        latest_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2] if len(rsi) > 1 else latest_rsi
        if prev_rsi <= self.oversold < latest_rsi:
            return {'symbol': symbol or self.symbol, 'action': 'buy', 'volume': self.volume}
        elif prev_rsi >= self.overbought > latest_rsi:
            return {'symbol': symbol or self.symbol, 'action': 'sell', 'volume': self.volume}
        return None

    def generate_exit_signal(self, position):
        """Generate an exit signal for an open position."""
        data = self.fetch_data(position.symbol)
        if data.empty:
            self.logger.warning(f"No data available for {position.symbol}")
            return None
        rsi = ta.momentum.RSIIndicator(close=data['close'], window=self.period).rsi()
        latest_rsi = rsi.iloc[-1]
        if position.type == mt5.ORDER_TYPE_BUY and latest_rsi >= self.overbought:
            return {'symbol': position.symbol, 'action': 'sell', 'volume': position.volume}
        elif position.type == mt5.ORDER_TYPE_SELL and latest_rsi <= self.oversold:
            return {'symbol': position.symbol, 'action': 'buy', 'volume': position.volume}
        return None