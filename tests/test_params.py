#!/usr/bin/env python3
"""Test different ways to define params in backtesting.py"""
from backtesting import Strategy, Backtest
import pandas as pd
import numpy as np

dates = pd.date_range("2020-01-01", periods=100, freq="D")
data = pd.DataFrame(
    {
        "Open": [100.0] * 100,
        "High": [101.0] * 100,
        "Low": [99.0] * 100,
        "Close": [100.0] * 100,
        "Volume": [1000] * 100,
    },
    index=dates,
)


# Test 1: No params - should work
class NoParams(Strategy):
    def init(self):
        pass

    def next(self):
        pass


try:
    bt = Backtest(data, NoParams)
    stats = bt.run()
    print("✓ Test 1 (no params): PASSED")
except Exception as e:
    print(f"✗ Test 1 (no params): FAILED - {e}")


# Test 2: params dict as class variable
class WithParams(Strategy):
    params = dict(period=14)

    def init(self):
        pass

    def next(self):
        pass


try:
    bt = Backtest(data, WithParams)
    stats = bt.run(period=14)
    print("✓ Test 2 (with params as dict): PASSED")
except Exception as e:
    print(f"✗ Test 2 (with params as dict): FAILED - {e}")

# Test 3: Check what params backtesting expects
try:
    print("\nWith Params class definition:")
    print("  WithParams.params:", WithParams.params)

    # Check internal structure
    test_strat = WithParams.__new__(WithParams)
    print("  Instance params:", getattr(test_strat, "params", "NOT FOUND"))
except Exception as e:
    print(f"Error checking params: {e}")
