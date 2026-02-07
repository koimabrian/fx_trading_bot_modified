"""
Comprehensive Untested Phase Tests with Proper Initialization
Tests all untested components with correct dependencies
"""

import sys
import os
import time

# Add project root to path for proper imports
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

from src.utils.logging_factory import LoggingFactory
from src.utils.config_manager import ConfigManager
from src.database.db_manager import DatabaseManager
from src.core.strategy_selector import StrategySelector
from src.backtesting.backtest_manager import BacktestManager
from src.core.mt5_connector import MT5Connector

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

    try:
        from src.core.data_fetcher import DataFetcher

        config = ConfigManager.get_config()
        db = DatabaseManager(config)
        db.connect()

        # Initialize MT5Connector for DataFetcher
        mt5_conn = MT5Connector(db)

        # Initialize DataFetcher with required parameters
        start = time.perf_counter()
        fetcher = DataFetcher(mt5_conn, db, config)
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

        # Assert initialization successful
        assert fetcher is not None, "DataFetcher initialization failed"
        assert (
            init_time < 1.0
        ), f"DataFetcher initialization took too long: {init_time}s"
        assert len(methods) > 0, "DataFetcher has no public methods"
        assert len(key_methods) > 0, "DataFetcher has no data methods"

        print("Status: PASS")

    except Exception as e:
        print(f"Error: {e}")
        raise


def test_strategy_selector():
    """Test StrategySelector"""
    log_section("UNTESTED: StrategySelector (Strategy Ranking & Selection)")

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

        # Assert initialization successful
        assert selector is not None, "StrategySelector initialization failed"
        assert (
            init_time < 1.0
        ), f"StrategySelector initialization took too long: {init_time}s"
        assert len(methods) > 0, "StrategySelector has no public methods"
        assert len(strategy_methods) > 0, "StrategySelector has no selection methods"

        print("Status: PASS")

    except Exception as e:
        print(f"Error: {e}")
        raise


def test_trade_manager_with_db():
    """Test TradeManager with Database"""
    log_section("UNTESTED: TradeManager (Trade Execution & Management)")

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

        # Assert initialization successful
        assert manager is not None, "TradeManager initialization failed"
        assert (
            init_time < 1.0
        ), f"TradeManager initialization took too long: {init_time}s"
        assert len(methods) > 0, "TradeManager has no public methods"
        assert len(trade_methods) > 0, "TradeManager has no trade methods"

        print("Status: PASS")

    except Exception as e:
        print(f"Error: {e}")
        raise


def test_backtest_manager():
    """Test BacktestManager"""
    log_section("UNTESTED: BacktestManager (Historical Simulation)")

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

        # Assert initialization successful
        assert manager is not None, "BacktestManager initialization failed"
        assert (
            init_time < 1.0
        ), f"BacktestManager initialization took too long: {init_time}s"
        assert len(methods) > 0, "BacktestManager has no public methods"
        assert len(backtest_methods) > 0, "BacktestManager has no backtest methods"

        print("Status: PASS")

    except Exception as e:
        print(f"Error: {e}")
        raise


def test_trade_monitor():
    """Test TradeMonitor"""
    log_section("UNTESTED: TradeMonitor (Real-Time Trade Monitoring)")

    try:
        from src.core.trade_monitor import TradeMonitor

        config = ConfigManager.get_config()
        db = DatabaseManager(config)
        db.connect()

        # Initialize MT5Connector for TradeMonitor
        mt5_conn = MT5Connector(db)

        # Initialize TradeMonitor with required parameters
        start = time.perf_counter()
        monitor = TradeMonitor(mt5_conn, db)
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

        # Assert initialization successful
        assert monitor is not None, "TradeMonitor initialization failed"
        assert (
            init_time < 1.0
        ), f"TradeMonitor initialization took too long: {init_time}s"
        assert len(methods) > 0, "TradeMonitor has no public methods"
        assert len(monitoring_methods) > 0, "TradeMonitor has no monitoring methods"

        print("Status: PASS")

    except Exception as e:
        print(f"Error: {e}")
        raise


def test_metrics_engine():
    """Test MetricsEngine"""
    log_section("UNTESTED: MetricsEngine (Performance Metrics)")

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

        # Assert initialization successful
        assert metrics is not None, "MetricsEngine initialization failed"
        assert (
            init_time < 1.0
        ), f"MetricsEngine initialization took too long: {init_time}s"
        assert len(methods) > 0, "MetricsEngine has no public methods"
        assert len(metrics_methods) > 0, "MetricsEngine has no metrics methods"

        print("Status: PASS")

    except Exception as e:
        print(f"Error: {e}")
        raise
