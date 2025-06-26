# fx_trading_bot/src/strategies/rsi_strategy.py
# Purpose: Implements RSI-based trading strategy
import ta
import pandas as pd
import MetaTrader5 as mt5
from src.core.base_strategy import BaseStrategy

class RSIStrategy(BaseStrategy):
    def __init__(self, params, db):
        super().__init__(params, db)
        self.period = params.get('period', 14)
        self.overbought = params.get('overbought', 70)
        self.oversold = params.get('oversold', 30)

    def generate_entry_signal(self, symbol=None):
        """Generate entry signal based on RSI"""
        data = self.fetch_data(symbol)
        if data.empty:
            self.logger.warning("No data available in database for RSI calculation")
            return None

        data['rsi'] = ta.momentum.RSIIndicator(data['close'], window=self.period).rsi()
        if len(data) < 2:
            return None

        latest_rsi = data['rsi'].iloc[-1]
        previous_rsi = data['rsi'].iloc[-2]

        # Entry signal: RSI crosses oversold (buy) or overbought (sell)
        if previous_rsi >= self.oversold and latest_rsi < self.oversold:
            self.logger.info(f"RSI Buy signal for {symbol or self.symbol}")
            return {'symbol': symbol or self.symbol, 'action': 'buy', 'volume': self.volume}
        elif previous_rsi <= self.overbought and latest_rsi > self.overbought:
            self.logger.info(f"RSI Sell signal for {symbol or self.symbol}")
            return {'symbol': symbol or self.symbol, 'action': 'sell', 'volume': self.volume}
        return None

    def generate_exit_signal(self, position):
        """Generate exit signal based on RSI reversal"""
        data = self.fetch_data(position.symbol)
        if data.empty:
            self.logger.warning("No data available in database for RSI exit signal")
            return None

        data['rsi'] = ta.momentum.RSIIndicator(data['close'], window=self.period).rsi()
        if len(data) < 2:
            return None

        latest_rsi = data['rsi'].iloc[-1]
        previous_rsi = data['rsi'].iloc[-2]

        # Exit signal: RSI reverses from overbought (close buy) or oversold (close sell)
        if position.type == mt5.ORDER_TYPE_BUY:
            if previous_rsi <= self.overbought and latest_rsi > self.overbought:
                self.logger.info(f"RSI Exit signal to close buy position for {position.symbol}")
                return True
        elif position.type == mt5.ORDER_TYPE_SELL:
            if previous_rsi >= self.oversold and latest_rsi < self.oversold:
                self.logger.info(f"RSI Exit signal to close sell position for {position.symbol}")
                return True
        return None