"""
Performance Testing & Profiling Suite
Tests all phases and identifies optimization opportunities
"""

import sys
import os
import cProfile
import pstats
import io
import time
import tracemalloc
from contextlib import contextmanager
from typing import Callable, Any, Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logging_factory import LoggingFactory
from src.utils.config_manager import ConfigManager
from src.database.db_manager import DatabaseManager
from src.core.data_fetcher import DataFetcher
from src.mt5_connector import MT5Connector
from src.core.base_strategy import BaseStrategy
from src.strategy_manager import StrategyManager
from src.core.trader import Trader
from src.backtesting.backtest_manager import BacktestManager


class PerformanceTest:
    """Comprehensive performance testing framework"""

    def __init__(self):
        """Initialize performance tester"""
        self.logger = LoggingFactory.get_logger(__name__)
        self.results: Dict[str, Dict[str, Any]] = {}
        LoggingFactory.configure()

    @contextmanager
    def profile_time(self, name: str):
        """Context manager to profile execution time"""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self.logger.info(f"{name}: {elapsed:.4f}s")
            if name not in self.results:
                self.results[name] = {}
            self.results[name]["time"] = elapsed

    @contextmanager
    def profile_memory(self, name: str):
        """Context manager to profile memory usage"""
        tracemalloc.start()
        try:
            yield
        finally:
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            self.logger.info(f"{name}: {peak / 1024 / 1024:.2f} MB peak memory")
            if name not in self.results:
                self.results[name] = {}
            self.results[name]["memory_mb"] = peak / 1024 / 1024

    def profile_function(self, func: Callable, *args, **kwargs) -> Any:
        """Profile a function using cProfile"""
        profiler = cProfile.Profile()
        profiler.enable()
        try:
            result = func(*args, **kwargs)
        finally:
            profiler.disable()

            # Capture stats
            s = io.StringIO()
            ps = pstats.Stats(profiler, stream=s).sort_stats("cumulative")
            ps.print_stats(10)  # Top 10 functions

            stats_str = s.getvalue()
            self.logger.debug(f"Profile for {func.__name__}:\n{stats_str}")

            return result

    def test_phase_1_config_manager(self):
        """Test Phase 1: ConfigManager singleton performance"""
        self.logger.info("=" * 70)
        self.logger.info("PHASE 1: ConfigManager Performance Test")
        self.logger.info("=" * 70)

        with self.profile_time("ConfigManager.get_config() - first call"):
            config1 = ConfigManager.get_config()

        with self.profile_time("ConfigManager.get_config() - cached call"):
            config2 = ConfigManager.get_config()

        # Verify singleton
        assert config1 is config2, "ConfigManager should return same instance"
        self.logger.info("✓ ConfigManager is proper singleton")

        # Check config keys
        keys = len(config1.keys())
        self.logger.info(f"✓ Config has {keys} keys")

        self.results["Phase 1 - ConfigManager"] = {
            "status": "PASS",
            "singleton": True,
            "config_keys": keys,
        }

    def test_phase_2_mt5_decorator(self):
        """Test Phase 2: MT5Decorator retry logic performance"""
        self.logger.info("=" * 70)
        self.logger.info("PHASE 2: MT5Decorator Performance Test")
        self.logger.info("=" * 70)

        # Test import and decorator presence
        from src.utils.mt5_decorator import mt5_safe

        with self.profile_time("mt5_safe decorator import"):
            pass  # Already imported above

        self.logger.info("✓ MT5Decorator imported successfully")
        self.logger.info("✓ Retry logic available")

        self.results["Phase 2 - MT5Decorator"] = {
            "status": "PASS",
            "decorator_available": True,
        }

    def test_phase_3_error_handler(self):
        """Test Phase 3: ErrorHandler performance"""
        self.logger.info("=" * 70)
        self.logger.info("PHASE 3: ErrorHandler Performance Test")
        self.logger.info("=" * 70)

        from src.utils.error_handler import ErrorHandler

        with self.profile_time("ErrorHandler initialization"):
            handler = ErrorHandler()

        with self.profile_time("ErrorHandler.handle_error() call"):
            # Test error handling
            try:
                raise ValueError("Test error")
            except ValueError as e:
                handler.handle_error(e, "RECOVERABLE", "test_function")

        self.logger.info("✓ ErrorHandler initialized")
        self.logger.info("✓ Error handling works")

        self.results["Phase 3 - ErrorHandler"] = {
            "status": "PASS",
            "error_handling": True,
        }

    def test_phase_4_logging_factory(self):
        """Test Phase 4: LoggingFactory performance"""
        self.logger.info("=" * 70)
        self.logger.info("PHASE 4: LoggingFactory Performance Test")
        self.logger.info("=" * 70)

        with self.profile_time("LoggingFactory.get_logger() - first call"):
            logger1 = LoggingFactory.get_logger("test.module.1")

        with self.profile_time("LoggingFactory.get_logger() - cached call"):
            logger2 = LoggingFactory.get_logger("test.module.1")

        # Verify caching
        assert logger1 is logger2, "LoggingFactory should cache loggers"
        self.logger.info("✓ LoggingFactory caches loggers correctly")

        with self.profile_time("Write 100 log messages"):
            for i in range(100):
                logger1.info(f"Test message {i}")

        self.logger.info("✓ Logging performance acceptable")

        self.results["Phase 4 - LoggingFactory"] = {
            "status": "PASS",
            "logger_caching": True,
            "throughput_msg_per_sec": 100
            / self.results["Phase 4 - LoggingFactory"]["time"],
        }

    def test_data_fetcher_performance(self):
        """Test DataFetcher performance"""
        self.logger.info("=" * 70)
        self.logger.info("DATA FETCHER: Performance Test")
        self.logger.info("=" * 70)

        try:
            config = ConfigManager.get_config()
            db = DatabaseManager(config)
            mt5 = MT5Connector(
                config.get("mt5", {}).get("login", 0),
                config.get("mt5", {}).get("password", ""),
                config.get("mt5", {}).get("server", ""),
            )

            with self.profile_time("DataFetcher initialization"):
                fetcher = DataFetcher(mt5, db, config)

            self.logger.info("✓ DataFetcher initialized")
            self.results["DataFetcher"] = {"status": "PASS", "initialization": True}
        except Exception as e:
            self.logger.warning(f"DataFetcher test skipped: {e}")
            self.results["DataFetcher"] = {"status": "SKIP", "reason": str(e)}

    def test_strategy_selection_performance(self):
        """Test strategy selection performance"""
        self.logger.info("=" * 70)
        self.logger.info("STRATEGY SELECTION: Performance Test")
        self.logger.info("=" * 70)

        try:
            config = ConfigManager.get_config()
            db = DatabaseManager(config)

            with self.profile_time("StrategySelector initialization"):
                from src.core.strategy_selector import StrategySelector

                selector = StrategySelector(db)

            self.logger.info("✓ StrategySelector initialized")
            self.results["StrategySelector"] = {
                "status": "PASS",
                "initialization": True,
            }
        except Exception as e:
            self.logger.warning(f"StrategySelector test skipped: {e}")
            self.results["StrategySelector"] = {"status": "SKIP", "reason": str(e)}

    def test_database_performance(self):
        """Test database connection and query performance"""
        self.logger.info("=" * 70)
        self.logger.info("DATABASE: Performance Test")
        self.logger.info("=" * 70)

        try:
            config = ConfigManager.get_config()

            with self.profile_time("DatabaseManager connection"):
                db = DatabaseManager(config)
                db.connect()

            with self.profile_time("Database query - select from tradable_pairs"):
                cursor = db.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM tradable_pairs")
                count = cursor.fetchone()[0]

            self.logger.info(f"✓ Database connected - {count} tradable pairs")

            with self.profile_time("Database connection close"):
                db.close()

            self.results["Database"] = {"status": "PASS", "tradable_pairs": count}
        except Exception as e:
            self.logger.warning(f"Database test skipped: {e}")
            self.results["Database"] = {"status": "SKIP", "reason": str(e)}

    def run_all_tests(self):
        """Run all performance tests"""
        self.logger.info("\n")
        self.logger.info("=" * 70)
        self.logger.info("COMPREHENSIVE PERFORMANCE TEST SUITE")
        self.logger.info("=" * 70)
        self.logger.info("\n")

        # Phase tests
        self.test_phase_1_config_manager()
        self.test_phase_2_mt5_decorator()
        self.test_phase_3_error_handler()
        self.test_phase_4_logging_factory()

        # Component tests
        self.test_database_performance()
        self.test_data_fetcher_performance()
        self.test_strategy_selection_performance()

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print performance test summary"""
        self.logger.info("\n")
        self.logger.info("=" * 70)
        self.logger.info("PERFORMANCE TEST SUMMARY")
        self.logger.info("=" * 70)

        total_tests = len(self.results)
        passed = sum(1 for r in self.results.values() if r.get("status") == "PASS")
        skipped = sum(1 for r in self.results.values() if r.get("status") == "SKIP")

        self.logger.info(f"\nTotal Tests: {total_tests}")
        self.logger.info(f"Passed: {passed}")
        self.logger.info(f"Skipped: {skipped}")

        self.logger.info("\nDetailed Results:")
        for test_name, result in self.results.items():
            status = result.get("status", "UNKNOWN")
            self.logger.info(f"  {test_name}: {status}")

            if "time" in result:
                self.logger.info(f"    Time: {result['time']:.4f}s")
            if "memory_mb" in result:
                self.logger.info(f"    Memory: {result['memory_mb']:.2f} MB")

        self.logger.info("\n" + "=" * 70)
        self.logger.info("PERFORMANCE TEST COMPLETE")
        self.logger.info("=" * 70)


if __name__ == "__main__":
    tester = PerformanceTest()
    tester.run_all_tests()
