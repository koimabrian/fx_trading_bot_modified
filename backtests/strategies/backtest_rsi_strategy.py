# fx_trading_bot/backtests/strategies/backtest_rsi_strategy.py
# Purpose: Implements RSI strategy for backtesting with VectorBT
import vectorbt as vbt
import pandas as pd
import ta

def run_rsi_strategy(data, period=14, overbought=70, oversold=30, size=0.1):
    """Run RSI strategy using VectorBT"""
    close = data['Close']
    rsi = ta.momentum.RSIIndicator(close, window=period).rsi()
    entries = rsi < oversold
    exits = rsi > overbought
    portfolio = vbt.Portfolio.from_signals(
        close=close,
        entries=entries,
        exits=exits,
        size=size,
        fees=0.001,
        freq='15min'
    )
    return portfolio