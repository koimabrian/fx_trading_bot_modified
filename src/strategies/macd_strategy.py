# src/strategies/macd_strategy.py
from src.core.base_strategy import BaseStrategy
import ta
import logging
import pandas as pd
import MetaTrader5 as mt5

class MACDStrategy(BaseStrategy):
    """MACD-based trading strategy."""
    def __init__(self, params, db, config, mode='live'):
        super().__init__(params, db, config, mode)
        self.fast_period = params.get('fast_period', 12)
        self.slow_period = params.get('slow_period', 26)
        self.signal_period = params.get('signal_period', 9)

    def generate_entry_signal(self, symbol=None):
        """Generate an entry signal based on MACD."""
        data = self.fetch_data(symbol)
        if data.empty:
            self.logger.warning(f"No data available for {symbol or self.symbol}")
            return None
        macd = ta.trend.MACD(
            close=data['close'],
            window_fast=self.fast_period,
            window_slow=self.slow_period,
            window_sign=self.signal_period
        )
        macd_line = macd.macd()
        signal_line = macd.macd_signal()
        if len(macd_line) < 2 or len(signal_line) < 2:
            self.logger.warning(f"Insufficient data for MACD calculation for {symbol or self.symbol}")
            return None
        latest_macd = macd_line.iloc[-1]
        prev_macd = macd_line.iloc[-2]
        latest_signal = signal_line.iloc[-1]
        prev_signal = signal_line.iloc[-2]
        # Buy signal: MACD crosses above signal line
        if prev_macd <= prev_signal and latest_macd > latest_signal:
            return {'symbol': symbol or self.symbol, 'action': 'buy', 'volume': self.volume}
        # Sell signal: MACD crosses below signal line
        elif prev_macd >= prev_signal and latest_macd < latest_signal:
            return {'symbol': symbol or self.symbol, 'action': 'sell', 'volume': self.volume}
        return None

    def generate_exit_signal(self, position):
        """Generate an exit signal for an open position."""
        data = self.fetch_data(position.symbol)
        if data.empty:
            self.logger.warning(f"No data available for {position.symbol}")
            return None
        macd = ta.trend.MACD(
            close=data['close'],
            window_fast=self.fast_period,
            window_slow=self.slow_period,
            window_sign=self.signal_period
        )
        macd_line = macd.macd()
        signal_line = macd.macd_signal()
        if len(macd_line) < 1 or len(signal_line) < 1:
            self.logger.warning(f"Insufficient data for MACD calculation for {position.symbol}")
            return None
        latest_macd = macd_line.iloc[-1]
        latest_signal = signal_line.iloc[-1]
        # Exit buy position: MACD crosses below signal line
        if position.type == mt5.ORDER_TYPE_BUY and latest_macd < latest_signal:
            return {'symbol': position.symbol, 'action': 'sell', 'volume': position.volume}
        # Exit sell position: MACD crosses above signal line
        elif position.type == mt5.ORDER_TYPE_SELL and latest_macd > latest_signal:
            return {'symbol': position.symbol, 'action': 'buy', 'volume': position.volume}
        return None