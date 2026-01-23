#!/usr/bin/env python3
"""Test different param definition methods"""
from backtesting import Strategy, Backtest
import pandas as pd

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


# Different ways to define params
class Style1(Strategy):
    """Using dict()"""

    params = dict(period=14)

    def init(self):
        pass

    def next(self):
        pass


class Style2(Strategy):
    """Using {}.update()"""

    params = {}
    params.update({"period": 14})

    def init(self):
        pass

    def next(self):
        pass


class Style3(Strategy):
    """Using literal dict"""

    params = {"period": 14}

    def init(self):
        pass

    def next(self):
        pass


class Style4(Strategy):
    """Using tuple of tuples (old backtesting API)"""

    params = (("period", 14),)

    def init(self):
        pass

    def next(self):
        pass


for style_class in [Style1, Style2, Style3, Style4]:
    try:
        bt = Backtest(data, style_class)
        stats = bt.run(period=14)
        print(f"✓ {style_class.__name__}: PASSED")
    except Exception as e:
        print(f"✗ {style_class.__name__}: FAILED")
        print(f"  Error: {str(e)[:100]}")
        print(f"  Params: {style_class.params}")
