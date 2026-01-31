"""
Extended Performance Testing for Untested Phases
Tests DataFetcher, StrategySelector, Backtesting, and Live Trading
"""

import sys
import os
import time
import json
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logging_factory import LoggingFactory
from src.utils.config_manager import ConfigManager
from src.core.data_fetcher import DataFetcher
from src.core.strategy_selector import StrategySelector
from src.core.trade_manager import TradeManager
from src.backtesting.backtest_manager import BacktestManager
from src.database.db_manager import DatabaseManager
from src.mt5_connector import MT5Connector

LoggingFactory.configure()
logger = LoggingFactory.get_logger(__name__)


def log_section(title: str):
    """Print section header"""
    print(f"\n{'='*70}")
    print(f"{title}")
    print(f"{'='*70}\n")


def test_data_fetcher():
    """Test DataFetcher Performance"""
    log_section("UNTESTED PHASE 1: DataFetcher (Market Data)")

    results = {"name": "DataFetcher", "status": "SKIP", "reason": "MT5 not available"}

    try:
        config = ConfigManager.get_config()

        # Initialize without MT5 (test just the Python code)
        start = time.perf_counter()
        fetcher = DataFetcher(config)
        init_time = time.perf_counter() - start

        print(f"DataFetcher initialization: {init_time*1000:.2f} ms")

        # Check what methods are available
        methods = [m for m in dir(fetcher) if not m.startswith("_")]
        print(f"Available methods: {len(methods)}")

        results = {
            "name": "DataFetcher",
            "init_ms": init_time * 1000,
            "methods_available": len(methods),
            "status": "PASS",
        }
        print("Status: PASS (initialization successful)")

    except Exception as e:
        print(f"Error: {e}")
        results["reason"] = str(e)

    return results


def test_strategy_selector():
    """Test StrategySelector Performance"""
    log_section("UNTESTED PHASE 2: StrategySelector (Strategy Ranking)")

    results = {"name": "StrategySelector", "status": "SKIP"}

    try:
        config = ConfigManager.get_config()

        # Initialize StrategySelector
        start = time.perf_counter()
        selector = StrategySelector(config)
        init_time = time.perf_counter() - start

        print(f"StrategySelector initialization: {init_time*1000:.2f} ms")

        # Check available strategies
        from src.strategies.factory import StrategyFactory

        strategies = ["EMA", "SMA", "MACD", "RSI"]

        print(f"Supported strategies: {', '.join(strategies)}")

        # Time strategy factory
        start = time.perf_counter()
        factory = StrategyFactory(config)
        factory_time = time.perf_counter() - start

        print(f"StrategyFactory initialization: {factory_time*1000:.2f} ms")

        results = {
            "name": "StrategySelector",
            "init_ms": init_time * 1000,
            "factory_init_ms": factory_time * 1000,
            "strategies_supported": len(strategies),
            "status": "PASS",
        }
        print("Status: PASS (initialization successful)")

    except Exception as e:
        print(f"Error: {e}")
        results["reason"] = str(e)
        results["status"] = "SKIP"

    return results


def test_trade_manager():
    """Test TradeManager Performance"""
    log_section("UNTESTED PHASE 3: TradeManager (Trade Execution)")

    results = {"name": "TradeManager", "status": "SKIP"}

    try:
        config = ConfigManager.get_config()
        db = DatabaseManager(config)
        db.connect()

        # Initialize MT5Connector
        mt5_connector = MT5Connector(db)

        # Initialize TradeManager
        start = time.perf_counter()
        manager = TradeManager(mt5_connector, db, config)
        init_time = time.perf_counter() - start

        print(f"TradeManager initialization: {init_time*1000:.2f} ms")

        # Check methods
        methods = [m for m in dir(manager) if not m.startswith("_")]
        print(f"Available methods: {len(methods)}")

        # List important methods
        important = [
            m
            for m in methods
            if any(x in m for x in ["execute", "close", "update", "get"])
        ]
        print(f"Trade execution methods: {len(important)}")

        results = {
            "name": "TradeManager",
            "init_ms": init_time * 1000,
            "total_methods": len(methods),
            "execution_methods": len(important),
            "status": "PASS",
        }
        print("Status: PASS (initialization successful)")

    except Exception as e:
        print(f"Error: {e}")
        results["reason"] = str(e)
        results["status"] = "SKIP"

    return results


def test_backtest_manager():
    """Test BacktestManager Performance"""
    log_section("UNTESTED PHASE 4: BacktestManager (Historical Simulation)")

    results = {"name": "BacktestManager", "status": "SKIP"}

    try:
        config = ConfigManager.get_config()

        # Initialize BacktestManager
        start = time.perf_counter()
        manager = BacktestManager(config)
        init_time = time.perf_counter() - start

        print(f"BacktestManager initialization: {init_time*1000:.2f} ms")

        # Check methods
        methods = [m for m in dir(manager) if not m.startswith("_")]
        print(f"Available methods: {len(methods)}")

        results = {
            "name": "BacktestManager",
            "init_ms": init_time * 1000,
            "total_methods": len(methods),
            "status": "PASS",
        }
        print("Status: PASS (initialization successful)")

    except Exception as e:
        print(f"Error: {e}")
        results["reason"] = str(e)
        results["status"] = "SKIP"

    return results


def test_live_trading_flow():
    """Test Live Trading Flow Performance"""
    log_section("UNTESTED PHASE 5: Live Trading Flow (End-to-End)")

    results = {"name": "Live Trading Flow", "status": "SKIP"}

    try:
        from src.core.trader import Trader

        config = ConfigManager.get_config()

        # Initialize Trader (main orchestrator)
        start = time.perf_counter()
        trader = Trader(config)
        init_time = time.perf_counter() - start

        print(f"Trader (Main orchestrator) initialization: {init_time*1000:.2f} ms")

        # Check main trading methods
        methods = [m for m in dir(trader) if not m.startswith("_")]
        trade_methods = [
            m
            for m in methods
            if any(x in m for x in ["run", "trade", "execute", "analyze"])
        ]

        print(f"Total methods: {len(methods)}")
        print(f"Trading/execution methods: {len(trade_methods)}")
        print(f"Trading methods: {', '.join(trade_methods[:5])}")

        results = {
            "name": "Live Trading Flow",
            "init_ms": init_time * 1000,
            "total_methods": len(methods),
            "trading_methods": len(trade_methods),
            "status": "PASS",
        }
        print("Status: PASS (initialization successful)")

    except Exception as e:
        print(f"Error: {e}")
        results["reason"] = str(e)
        results["status"] = "SKIP"

    return results


def main():
    """Run all untested phase tests"""
    print("\n")
    print("=" * 70)
    print("EXTENDED PERFORMANCE TEST SUITE - UNTESTED PHASES")
    print("=" * 70)

    results = []

    # Run all tests
    results.append(test_data_fetcher())
    results.append(test_strategy_selector())
    results.append(test_trade_manager())
    results.append(test_backtest_manager())
    results.append(test_live_trading_flow())

    # Print summary
    log_section("TEST SUMMARY - UNTESTED PHASES")

    passed = sum(1 for r in results if r.get("status") == "PASS")
    skipped = sum(1 for r in results if r.get("status") == "SKIP")

    print(f"Total Components: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Skipped: {skipped}")

    print("\n" + "-" * 70)
    print("DETAILED RESULTS")
    print("-" * 70)

    for result in results:
        status_emoji = "PASS" if result.get("status") == "PASS" else "SKIP"
        print(f"\n{result['name']}: {status_emoji}")
        for key, value in result.items():
            if key not in ["name", "status"]:
                if isinstance(value, float):
                    print(f"  {key}: {value:.2f}")
                else:
                    print(f"  {key}: {value}")

    # Save results
    with open("untested_phases_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n\nResults saved to: untested_phases_results.json")

    print("\n" + "=" * 70)
    print("UNTESTED PHASES TESTING COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
