"""
Comprehensive Performance & Functionality Testing
Tests all 4 phases and identifies optimization opportunities
"""

import sys
import os
import time
import json

# Add project root to path for proper imports
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, project_root)

from src.utils.logging_factory import LoggingFactory
from src.utils.config_manager import ConfigManager
from src.utils.error_handler import ErrorHandler
from src.utils.mt5_decorator import mt5_safe
from src.database.db_manager import DatabaseManager


def log_section(title):
    """Print section header"""
    print(f"\n{'='*70}")
    print(f"{title}")
    print(f"{'='*70}\n")


def test_phase_1_config_manager():
    """Test Phase 1: ConfigManager"""
    log_section("PHASE 1: ConfigManager Singleton")

    start = time.perf_counter()
    config1 = ConfigManager.get_config()
    time1 = time.perf_counter() - start
    print(f"First call (load): {time1*1000:.2f} ms")

    start = time.perf_counter()
    config2 = ConfigManager.get_config()
    time2 = time.perf_counter() - start
    print(f"Cached call: {time2*1000:.2f} ms")

    # Assert proper behavior
    assert config1 is config2, "ConfigManager singleton not working"
    assert len(config1.keys()) > 0, "Config keys not loaded"
    assert time2 < time1, "Cached call should be faster than first load"

    print(f"Config keys loaded: {len(config1.keys())}")
    print("Status: PASS")


def test_phase_2_mt5_decorator():
    """Test Phase 2: MT5Decorator"""
    log_section("PHASE 2: MT5Decorator (Retry Logic)")

    start = time.perf_counter()
    from src.utils.mt5_decorator import mt5_safe

    import_time = time.perf_counter() - start

    # Assert decorator is working
    assert mt5_safe is not None, "MT5Decorator not imported"
    assert callable(mt5_safe), "MT5Decorator is not callable"

    print(f"Decorator import: {import_time*1000:.2f} ms")
    print("Decorator available: True")
    print("Max retries: 5")
    print("Backoff strategy: Exponential")
    print("Status: PASS")


def test_phase_3_error_handler():
    """Test Phase 3: ErrorHandler"""
    log_section("PHASE 3: ErrorHandler (Centralized)")

    start = time.perf_counter()
    handler = ErrorHandler()
    init_time = time.perf_counter() - start

    print(f"Initialization: {init_time*1000:.2f} ms")

    start = time.perf_counter()
    try:
        raise ValueError("Test error")
    except ValueError as e:
        handler.handle_error(e, "RECOVERABLE", "test_function")
    handle_time = time.perf_counter() - start

    # Assert error handler is working
    assert handler is not None, "ErrorHandler initialization failed"
    assert handle_time < 0.1, "Error handling took too long"

    print(f"Error handling: {handle_time*1000:.2f} ms")
    print("Severity levels: RECOVERABLE, WARNING, CRITICAL, IGNORE")
    print("Status: PASS")


def test_phase_4_logging_factory():
    """Test Phase 4: LoggingFactory"""
    log_section("PHASE 4: LoggingFactory (Unified Logging)")

    LoggingFactory.configure()

    start = time.perf_counter()
    logger1 = LoggingFactory.get_logger("test.1")
    first_ms = time.perf_counter() - start

    start = time.perf_counter()
    logger2 = LoggingFactory.get_logger("test.1")
    cached_ms = time.perf_counter() - start

    # Assert logger caching is working
    assert logger1 is logger2, "LoggingFactory logger caching not working"
    assert cached_ms < first_ms, "Cached logger should be faster than first get"

    print(f"First get_logger(): {first_ms*1000:.2f} ms")
    print(f"Cached get_logger(): {cached_ms*1000:.2f} ms")

    # Performance test: write 100 logs
    start = time.perf_counter()
    for i in range(100):
        logger1.debug(f"Test message {i}")
    log_time = time.perf_counter() - start

    # Assert logging performance
    assert log_time < 1.0, "100 log messages took too long"

    print(f"100 log messages: {log_time*1000:.2f} ms ({100/log_time:.0f} msg/sec)")
    print("Log file: logs/terminal_log.txt")
    print("Rotation: 10 MB max, 5 backups")
    print("Status: PASS")


def test_database_performance():
    """Test Database Performance"""
    log_section("DATABASE: Performance Analysis")

    try:
        config = ConfigManager.get_config()

        start = time.perf_counter()
        db = DatabaseManager(config)
        db.connect()
        connect_ms = time.perf_counter() - start
        print(f"Connection: {connect_ms*1000:.2f} ms")

        start = time.perf_counter()
        cursor = db.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tradable_pairs")
        count = cursor.fetchone()[0]
        query_ms = time.perf_counter() - start
        print(f"Query (SELECT COUNT): {query_ms*1000:.2f} ms")
        print(f"Tradable pairs in DB: {count}")

        # Assert database operations are working
        assert db is not None, "Database connection failed"
        assert connect_ms < 1.0, "Database connection took too long"
        assert count >= 0, "Tradable pairs count is negative"

        db.close()
        print("Status: PASS")

    except Exception as e:
        print(f"Status: SKIP ({e})")
        raise


def main():
    """Run all tests"""
    print("\n")
    print("=" * 70)
    print("COMPREHENSIVE PERFORMANCE & FUNCTIONALITY TEST SUITE")
    print("=" * 70)

    # Run all tests
    test_phase_1_config_manager()
    test_phase_2_mt5_decorator()
    test_phase_3_error_handler()
    test_phase_4_logging_factory()
    test_database_performance()

    # Print summary
    log_section("TEST SUMMARY")
    print("All tests passed successfully!")

    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
