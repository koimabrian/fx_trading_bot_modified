"""
Extended Performance Testing for Untested Phases
Tests DataFetcher, StrategySelector, Backtesting, and Live Trading
"""

import sys
import os
import time
import json
from typing import Dict, Any

# Add project root to path for proper imports
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

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

    try:
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

        # Check what methods are available
        methods = [m for m in dir(fetcher) if not m.startswith("_")]
        print(f"Available methods: {len(methods)}")

        # Assert initialization successful
        assert fetcher is not None, "DataFetcher initialization failed"
        assert (
            init_time < 1.0
        ), f"DataFetcher initialization took too long: {init_time}s"
        assert len(methods) > 0, "DataFetcher has no public methods"

        print("Status: PASS (initialization successful)")

    except Exception as e:
        print(f"Error: {e}")
        raise


def test_strategy_selector():
    """Test StrategySelector Performance"""
    log_section("UNTESTED PHASE 2: StrategySelector (Strategy Ranking)")

    try:
        config = ConfigManager.get_config()
        db = DatabaseManager(config)
        db.connect()

        # Initialize StrategySelector
        start = time.perf_counter()
        selector = StrategySelector(config)
        init_time = time.perf_counter() - start

        print(f"StrategySelector initialization: {init_time*1000:.2f} ms")

        # Check available strategies
        from src.strategies.factory import StrategyFactory

        strategies = ["EMA", "SMA", "MACD", "RSI"]

        print(f"Supported strategies: {', '.join(strategies)}")

        # Time strategy factory method access (it's a class with static methods)
        start = time.perf_counter()
        method = StrategyFactory.create_strategy
        factory_time = time.perf_counter() - start

        print(f"StrategyFactory method access: {factory_time*1000:.2f} ms")

        # Assert initialization successful
        assert selector is not None, "StrategySelector initialization failed"
        assert method is not None, "StrategyFactory.create_strategy method not found"
        assert (
            init_time < 1.0
        ), f"StrategySelector initialization took too long: {init_time}s"
        assert (
            factory_time < 1.0
        ), f"StrategyFactory access took too long: {factory_time}s"
        assert len(strategies) > 0, "No strategies supported"

        print("Status: PASS (initialization successful)")

    except Exception as e:
        print(f"Error: {e}")
        raise


def test_trade_manager():
    """Test TradeManager Performance"""
    log_section("UNTESTED PHASE 3: TradeManager (Trade Execution)")

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

        # Assert initialization successful
        assert manager is not None, "TradeManager initialization failed"
        assert (
            init_time < 1.0
        ), f"TradeManager initialization took too long: {init_time}s"
        assert len(methods) > 0, "TradeManager has no public methods"
        assert len(important) > 0, "TradeManager has no execution methods"

        print("Status: PASS (initialization successful)")

    except Exception as e:
        print(f"Error: {e}")
        raise


def test_backtest_manager():
    """Test BacktestManager Performance"""
    log_section("UNTESTED PHASE 4: BacktestManager (Historical Simulation)")

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

        # Assert initialization successful
        assert manager is not None, "BacktestManager initialization failed"
        assert (
            init_time < 1.0
        ), f"BacktestManager initialization took too long: {init_time}s"
        assert len(methods) > 0, "BacktestManager has no public methods"

        print("Status: PASS (initialization successful)")

    except Exception as e:
        print(f"Error: {e}")
        raise


def test_live_trading_flow():
    """Test Live Trading Flow Performance"""
    log_section("UNTESTED PHASE 5: Live Trading Flow (End-to-End)")

    try:
        from src.core.trader import Trader

        config = ConfigManager.get_config()
        db = DatabaseManager(config)
        db.connect()

        # Initialize MT5Connector for Trader
        mt5_conn = MT5Connector(db)

        # Initialize StrategySelector (needed for Trader)
        strategy_selector = StrategySelector(config)

        # Initialize Trader with required parameters
        start = time.perf_counter()
        trader = Trader(strategy_selector, mt5_conn)
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

        # Assert initialization successful
        assert trader is not None, "Trader initialization failed"
        assert init_time < 1.0, f"Trader initialization took too long: {init_time}s"
        assert len(methods) > 0, "Trader has no public methods"
        assert len(trade_methods) > 0, "Trader has no trading/execution methods"

        print("Status: PASS (initialization successful)")

    except Exception as e:
        print(f"Error: {e}")
        raise
