# fx_trading_bot/src/strategies/macd_strategy.py
# Purpose: Implements MACD-based trading strategy
import pandas as pd
import ta
import logging
from src.core.base_strategy import BaseStrategy
from backtesting import Strategy

class MACDStrategy(BaseStrategy):
    def __init__(self, params, db, config, mode='live'):
        super().__init__(params, db, config, mode)
        self.fast_period = params.get('fast_period', 12)
        self.slow_period = params.get('slow_period', 26)
        self.signal_period = params.get('signal_period', 9)
        self.backtest_strategy = self.BacktestMACDStrategy

    def generate_entry_signal(self, symbol=None):
        """Generate entry signal based on MACD"""
        data = self.fetch_data(symbol)
        if data.empty:
            self.logger.warning(f"No data available for {symbol or self.symbol}")
            return None

        macd = ta.MACD(data['close'], window_fast=self.fast_period, window_slow=self.slow_period, window_sign=self.signal_period)
        data['macd'] = macd.macd()
        data['macd_signal'] = macd.macd_signal()
        data['macd_hist'] = macd.macd_diff()
        latest = data.iloc[-1]
        prev = data.iloc[-2] if len(data) > 1 else None

        if prev is None:
            return None

        signal = {
            'symbol': symbol or self.symbol,
            'volume': self.volume,
            'timeframe': self.timeframe
        }

        if latest['macd'] > latest['macd_signal'] and prev['macd'] <= prev['macd_signal']:
            signal['action'] = 'buy'
            self.logger.debug(f"Buy signal generated for {signal['symbol']}: MACD crossover")
            return signal
        elif latest['macd'] < latest['macd_signal'] and prev['macd'] >= prev['macd_signal']:
            signal['action'] = 'sell'
            self.logger.debug(f"Sell signal generated for {signal['symbol']}: MACD crossunder")
            return signal
        return None

    def generate_exit_signal(self, position):
        """Generate exit signal based on MACD"""
        data = self.fetch_data(position.symbol)
        if data.empty:
            self.logger.warning(f"No data available for {position.symbol}")
            return False

        macd = ta.MACD(data['close'], window_fast=self.fast_period, window_slow=self.slow_period, window_sign=self.signal_period)
        data['macd'] = macd.macd()
        data['macd_signal'] = macd.macd_signal()
        latest = data.iloc[-1]

        if position.type == 0:  # Buy position
            if latest['macd'] < latest['macd_signal']:
                self.logger.debug(f"Exit buy signal for {position.symbol}: MACD crossunder")
                return True
        else:  # Sell position
            if latest['macd'] > latest['macd_signal']:
                self.logger.debug(f"Exit sell signal for {position.symbol}: MACD crossover")
                return True
        return False

    class BacktestMACDStrategy(Strategy):
        def init(self):
            macd = ta.MACD(pd.Series(self.data.Close), window_fast=self.fast_period, window_slow=self.slow_period, window_sign=self.signal_period)
            self.macd = self.I(macd.macd)
            self.signal = self.I(macd.macd_signal)

        def next(self):
            if self.macd[-1] > self.signal[-1] and self.macd[-2] <= self.signal[-2]:
                self.buy(size=self.volume)
            elif self.macd[-1] < self.signal[-1] and self.macd[-2] >= self.signal[-2]:
                self.sell(size=self.volume)