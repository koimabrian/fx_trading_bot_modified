# fx_trading_bot/backtests/strategies/backtest_macd_strategy.py
# Purpose: Implements MACD strategy for backtesting with VectorBT
import vectorbt as vbt
import pandas as pd
import ta

def run_macd_strategy(data, fast_period=12, slow_period=26, signal_period=9, size=0.1):
    """Run MACD strategy using VectorBT"""
    close = data['Close']
    macd = ta.trend.MACD(close, window_fast=fast_period, window_slow=slow_period, window_sign=signal_period)
    macd_line = macd.macd()
    signal_line = macd.macd_signal()
    entries = macd_line > signal_line
    exits = macd_line < signal_line
    portfolio = vbt.Portfolio.from_signals(
        close=close,
        entries=entries,
        exits=exits,
        size=size,
        fees=0.001,
        freq='15min'
    )
    return portfolio