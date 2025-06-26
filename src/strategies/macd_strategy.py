# fx_trading_bot/src/strategies/macd_strategy.py
# Purpose: Implements MACD-based trading strategy
import ta
import pandas as pd
import MetaTrader5 as mt5
from src.core.base_strategy import BaseStrategy

class MACDStrategy(BaseStrategy):
    def __init__(self, params, db):
        super().__init__(params, db)
        self.fast_period = params.get('fast_period', 12)
        self.slow_period = params.get('slow_period', 26)
        self.signal_period = params.get('signal_period', 9)

    def generate_entry_signal(self, symbol=None):
        """Generate entry signal based on MACD"""
        data = self.fetch_data(symbol)
        if data.empty:
            self.logger.warning("No data available in database for MACD calculation")
            return None

        macd = ta.trend.MACD(data['close'], window_fast=self.fast_period,
                             window_slow=self.slow_period, window_sign=self.signal_period)
        data['macd'] = macd.macd()
        data['signal'] = macd.macd_signal()
        if len(data) < 2:
            return None

        latest_macd = data['macd'].iloc[-1]
        latest_signal = data['signal'].iloc[-1]
        previous_macd = data['macd'].iloc[-2]
        previous_signal = data['signal'].iloc[-2]

        # Entry signal: MACD crosses above signal line (buy) or below (sell)
        if previous_macd < previous_signal and latest_macd > latest_signal:
            self.logger.info(f"MACD Buy signal for {symbol or self.symbol}")
            return {'symbol': symbol or self.symbol, 'action': 'buy', 'volume': self.volume}
        elif previous_macd > previous_signal and latest_macd < latest_signal:
            self.logger.info(f"MACD Sell signal for {symbol or self.symbol}")
            return {'symbol': symbol or self.symbol, 'action': 'sell', 'volume': self.volume}
        return None

    def generate_exit_signal(self, position):
        """Generate exit signal based on MACD reversal"""
        data = self.fetch_data(position.symbol)
        if data.empty:
            self.logger.warning("No data available in database for MACD exit signal")
            return None

        macd = ta.trend.MACD(data['close'], window_fast=self.fast_period,
                             window_slow=self.slow_period, window_sign=self.signal_period)
        data['macd'] = macd.macd()
        data['signal'] = macd.macd_signal()
        if len(data) < 2:
            return None

        latest_macd = data['macd'].iloc[-1]
        latest_signal = data['signal'].iloc[-1]
        previous_macd = data['macd'].iloc[-2]
        previous_signal = data['signal'].iloc[-2]

        # Exit signal: MACD reverses below signal line (close buy) or above (close sell)
        if position.type == mt5.ORDER_TYPE_BUY:
            if previous_macd > previous_signal and latest_macd < latest_signal:
                self.logger.info(f"MACD Exit signal to close buy position for {position.symbol}")
                return True
        elif position.type == mt5.ORDER_TYPE_SELL:
            if previous_macd < previous_signal and latest_macd > latest_signal:
                self.logger.info(f"MACD Exit signal to close sell position for {position.symbol}")
                return True
        return None