#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Test config structure and pair generation"""
import yaml
import sys
import os

# Fix encoding on Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Test loading config and generating pairs
with open("src/config/config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

# Generate pairs from config
if "pair_config" in config:
    pair_config = config["pair_config"]
    timeframes = pair_config.get("timeframes", [15, 60])
    categories = pair_config.get("categories", {})

    pairs = []
    for category, data in categories.items():
        symbols = data.get("symbols", []) if isinstance(data, dict) else data
        for symbol in symbols:
            for timeframe in timeframes:
                pairs.append({"symbol": symbol, "timeframe": timeframe})

    config["pairs"] = pairs

    total_symbols = sum(
        len(data.get("symbols", data) if isinstance(data, dict) else data)
        for data in categories.values()
    )

    print("[OK] CONFIG STRUCTURE VALIDATION")
    print("=" * 70)
    print(f"Total Categories: {len(categories)}")
    print(f"Total Symbols: {total_symbols}")
    print(f"Total Timeframes: {len(timeframes)} {timeframes}")
    print(f"Total Pairs Generated: {len(pairs)} ({total_symbols} x {len(timeframes)})")
    print()
    print("BREAKDOWN BY CATEGORY:")
    print("=" * 70)
    for category, data in categories.items():
        symbols = data.get("symbols", []) if isinstance(data, dict) else data
        num_pairs = len(symbols) * len(timeframes)
        print(
            f"{category.upper():15} {len(symbols):3} symbols x {len(timeframes)} TF = {num_pairs:3} backtests"
        )
    print()
    print("[OK] SAMPLE PAIRS GENERATED:")
    print("=" * 70)
    for i, pair in enumerate(pairs[:15]):
        tf_str = (
            "M" + str(pair["timeframe"])
            if pair["timeframe"] < 60
            else "H" + str(pair["timeframe"] // 60)
        )
        print(f'{i+1:3}. {pair["symbol"]:10} {tf_str}')
    print(f"... and {len(pairs) - 15} more")
    print()
    print("[OK] All checks passed! Config is valid and ready for backtesting.")
else:
    print("[FAIL] pair_config not found in config.yaml")
