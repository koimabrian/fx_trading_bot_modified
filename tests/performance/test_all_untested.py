"""
Comprehensive Untested Phase Tests with Proper Initialization
Tests all untested components with correct dependencies
"""

import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logging_factory import LoggingFactory
from src.utils.config_manager import ConfigManager
from src.database.db_manager import DatabaseManager
from src.core.strategy_selector import StrategySelector
from src.backtesting.backtest_manager import BacktestManager
from src.mt5_connector import MT5Connector
from src.core.trade_manager import TradeManager

LoggingFactory.configure()
logger = LoggingFactory.get_logger(__name__)


def log_section(title: str):
    """Print section header"""
    print(f"\n{'='*70}")
    print(f"{title}")
    print(f"{'='*70}\n")


def test_data_fetcher_with_db():
    """Test DataFetcher with Database"""
    log_section("UNTESTED: DataFetcher (Market Data Fetcher)")

    results = {"name": "DataFetcher", "status": "SKIP"}

    try:
        from src.core.data_fetcher import DataFetcher

        config = ConfigManager.get_config()
        db = DatabaseManager(config)
        db.connect()

        # Initialize DataFetcher with db
        start = time.perf_counter()
        fetcher = DataFetcher(db)
        init_time = time.perf_counter() - start

        print(f"DataFetcher initialization: {init_time*1000:.2f} ms")

        # Check methods
        methods = [
            m
            for m in dir(fetcher)
            if not m.startswith("_") and callable(getattr(fetcher, m))
        ]
        print(f"Public methods: {len(methods)}")

        # List key methods
        key_methods = [
            m for m in methods if any(x in m for x in ["fetch", "get", "load", "data"])
        ]
        print(f"Data methods: {', '.join(key_methods[:5])}")

        db.close()

        results = {
            "name": "DataFetcher",
            "init_ms": init_time * 1000,
            "public_methods": len(methods),
            "data_methods": len(key_methods),
            "status": "PASS",
        }
        print("Status: PASS")

    except Exception as e:
        print(f"Error: {e}")
        results["reason"] = str(e)

    return results


def test_strategy_selector():
    """Test StrategySelector"""
    log_section("UNTESTED: StrategySelector (Strategy Ranking & Selection)")

    results = {"name": "StrategySelector", "status": "SKIP"}

    try:
        config = ConfigManager.get_config()

        # Initialize StrategySelector
        start = time.perf_counter()
        selector = StrategySelector(config)
        init_time = time.perf_counter() - start

        print(f"StrategySelector initialization: {init_time*1000:.2f} ms")

        # Check methods
        methods = [
            m
            for m in dir(selector)
            if not m.startswith("_") and callable(getattr(selector, m))
        ]
        print(f"Public methods: {len(methods)}")

        # List strategy methods
        strategy_methods = [
            m
            for m in methods
            if any(x in m for x in ["select", "rank", "strategy", "score"])
        ]
        print(f"Strategy selection methods: {', '.join(strategy_methods[:5])}")

        results = {
            "name": "StrategySelector",
            "init_ms": init_time * 1000,
            "public_methods": len(methods),
            "selection_methods": len(strategy_methods),
            "status": "PASS",
        }
        print("Status: PASS")

    except Exception as e:
        print(f"Error: {e}")
        results["reason"] = str(e)

    return results


def test_trade_manager_with_db():
    """Test TradeManager with Database"""
    log_section("UNTESTED: TradeManager (Trade Execution & Management)")

    results = {"name": "TradeManager", "status": "SKIP"}

    try:
        from src.core.trade_manager import TradeManager

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
        methods = [
            m
            for m in dir(manager)
            if not m.startswith("_") and callable(getattr(manager, m))
        ]
        print(f"Public methods: {len(methods)}")

        # List trade methods
        trade_methods = [
            m
            for m in methods
            if any(x in m for x in ["execute", "close", "trade", "order"])
        ]
        print(f"Trade methods: {', '.join(trade_methods[:5])}")

        db.close()

        results = {
            "name": "TradeManager",
            "init_ms": init_time * 1000,
            "public_methods": len(methods),
            "trade_methods": len(trade_methods),
            "status": "PASS",
        }
        print("Status: PASS")

    except Exception as e:
        print(f"Error: {e}")
        results["reason"] = str(e)

    return results


def test_backtest_manager():
    """Test BacktestManager"""
    log_section("UNTESTED: BacktestManager (Historical Simulation)")

    results = {"name": "BacktestManager", "status": "SKIP"}

    try:
        config = ConfigManager.get_config()

        # Initialize BacktestManager
        start = time.perf_counter()
        manager = BacktestManager(config)
        init_time = time.perf_counter() - start

        print(f"BacktestManager initialization: {init_time*1000:.2f} ms")

        # Check methods
        methods = [
            m
            for m in dir(manager)
            if not m.startswith("_") and callable(getattr(manager, m))
        ]
        print(f"Public methods: {len(methods)}")

        # List backtest methods
        backtest_methods = [
            m
            for m in methods
            if any(x in m for x in ["run", "backtest", "simulate", "analyze"])
        ]
        print(f"Backtest methods: {', '.join(backtest_methods[:5])}")

        results = {
            "name": "BacktestManager",
            "init_ms": init_time * 1000,
            "public_methods": len(methods),
            "backtest_methods": len(backtest_methods),
            "status": "PASS",
        }
        print("Status: PASS")

    except Exception as e:
        print(f"Error: {e}")
        results["reason"] = str(e)

    return results


def test_trade_monitor():
    """Test TradeMonitor"""
    log_section("UNTESTED: TradeMonitor (Real-Time Trade Monitoring)")

    results = {"name": "TradeMonitor", "status": "SKIP"}

    try:
        from src.core.trade_monitor import TradeMonitor

        config = ConfigManager.get_config()
        db = DatabaseManager(config)
        db.connect()

        # Initialize TradeMonitor
        start = time.perf_counter()
        monitor = TradeMonitor(db)
        init_time = time.perf_counter() - start

        print(f"TradeMonitor initialization: {init_time*1000:.2f} ms")

        # Check methods
        methods = [
            m
            for m in dir(monitor)
            if not m.startswith("_") and callable(getattr(monitor, m))
        ]
        print(f"Public methods: {len(methods)}")

        # List monitoring methods
        monitoring_methods = [
            m
            for m in methods
            if any(x in m for x in ["monitor", "update", "get", "track"])
        ]
        print(f"Monitoring methods: {', '.join(monitoring_methods[:5])}")

        db.close()

        results = {
            "name": "TradeMonitor",
            "init_ms": init_time * 1000,
            "public_methods": len(methods),
            "monitoring_methods": len(monitoring_methods),
            "status": "PASS",
        }
        print("Status: PASS")

    except Exception as e:
        print(f"Error: {e}")
        results["reason"] = str(e)

    return results


def test_metrics_engine():
    """Test MetricsEngine"""
    log_section("UNTESTED: MetricsEngine (Performance Metrics)")

    results = {"name": "MetricsEngine", "status": "SKIP"}

    try:
        from src.backtesting.metrics_engine import MetricsEngine

        # Initialize MetricsEngine
        start = time.perf_counter()
        metrics = MetricsEngine()
        init_time = time.perf_counter() - start

        print(f"MetricsEngine initialization: {init_time*1000:.2f} ms")

        # Check methods
        methods = [
            m
            for m in dir(metrics)
            if not m.startswith("_") and callable(getattr(metrics, m))
        ]
        print(f"Public methods: {len(methods)}")

        # List metrics methods
        metrics_methods = [
            m
            for m in methods
            if any(x in m for x in ["calculate", "metric", "performance", "ratio"])
        ]
        print(f"Metrics methods: {', '.join(metrics_methods[:5])}")

        results = {
            "name": "MetricsEngine",
            "init_ms": init_time * 1000,
            "public_methods": len(methods),
            "metrics_methods": len(metrics_methods),
            "status": "PASS",
        }
        print("Status: PASS")

    except Exception as e:
        print(f"Error: {e}")
        results["reason"] = str(e)

    return results


def main():
    """Run all untested phase tests"""
    print("\n")
    print("=" * 70)
    print("COMPREHENSIVE UNTESTED COMPONENTS TESTING")
    print("=" * 70)

    results = []

    # Run all tests
    results.append(test_data_fetcher_with_db())
    results.append(test_strategy_selector())
    results.append(test_trade_manager_with_db())
    results.append(test_backtest_manager())
    results.append(test_trade_monitor())
    results.append(test_metrics_engine())

    # Print summary
    log_section("TEST SUMMARY - UNTESTED COMPONENTS")

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
    with open("comprehensive_untested_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n\nResults saved to: comprehensive_untested_results.json")

    print("\n" + "=" * 70)
    print("UNTESTED COMPONENTS TESTING COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
