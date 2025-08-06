# fx_trading_bot/src/strategies/rsi_strategy.py
# Purpose: Implements RSI-based trading strategy
import pandas as pd
import ta
import logging
from src.core.base_strategy import BaseStrategy
from backtesting import Strategy

class RSIStrategy(BaseStrategy):
    def __init__(self, params, db, config, mode='live'):
        super().__init__(params, db, config, mode)
        self.period = params.get('period', 14)
        self.overbought = params.get('overbought', 70)
        self.oversold = params.get('oversold', 30)
        self.backtest_strategy = self.BacktestRSIStrategy

    def generate_entry_signal(self, symbol=None):
        """Generate entry signal based on RSI"""
        data = self.fetch_data(symbol)
        if data.empty:
            self.logger.warning(f"No data available for {symbol or self.symbol}")
            return None

        data['rsi'] = ta.RSIIndicator(data['close'], window=self.period).rsi()
        latest = data.iloc[-1]
        prev = data.iloc[-2] if len(data) > 1 else None

        if prev is None:
            return None

        signal = {
            'symbol': symbol or self.symbol,
            'volume': self.volume,
            'timeframe': self.timeframe
        }

        if latest['rsi'] < self.oversold and prev['rsi'] >= self.oversold:
            signal['action'] = 'buy'
            self.logger.debug(f"Buy signal generated for {signal['symbol']}: RSI={latest['rsi']:.2f}")
            return signal
        elif latest['rsi'] > self.overbought and prev['rsi'] <= self.overbought:
            signal['action'] = 'sell'
            self.logger.debug(f"Sell signal generated for {signal['symbol']}: RSI={latest['rsi']:.2f}")
            return signal
        return None

    def generate_exit_signal(self, position):
        """Generate exit signal based on RSI"""
        data = self.fetch_data(position.symbol)
        if data.empty:
            self.logger.warning(f"No data available for {position.symbol}")
            return False

        data['rsi'] = ta.RSIIndicator(data['close'], window=self.period).rsi()
        latest = data.iloc[-1]

        if position.type == 0:  # Buy position
            if latest['rsi'] > self.overbought:
                self.logger.debug(f"Exit buy signal for {position.symbol}: RSI={latest['rsi']:.2f}")
                return True
        else:  # Sell position
            if latest['rsi'] < self.oversold:
                self.logger.debug(f"Exit sell signal for {position.symbol}: RSI={latest['rsi']:.2f}")
                return True
        return False

    class BacktestRSIStrategy(Strategy):
        def init(self):
            self.rsi = self.I(lambda x: ta.RSIIndicator(pd.Series(x), window=self.period).rsi(), self.data.Close)

        def next(self):
            if self.rsi[-1] < self.oversold and self.rsi[-2] >= self.oversold:
                self.buy(size=self.volume)
            elif self.rsi[-1] > self.overbought and self.rsi[-2] <= self.overbought:
                self.sell(size=self.volume)