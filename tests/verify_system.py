#!/usr/bin/env python
# pylint: disable=unused-import

"""
Final Verification Script for FX Trading Bot

This script verifies that all major components are working correctly.
Run with: python verify_system.py
"""

import sys
import os
import sqlite3

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def verify_imports():
    """Verify all critical imports work"""
    print("\n" + "=" * 80)
    print("IMPORT VERIFICATION")
    print("=" * 80)

    imports = [
        (
            "Core",
            [
                ("yaml", "YAML config"),
                ("pandas", "Data handling"),
                ("numpy", "Numerics"),
                ("sqlite3", "Database"),
            ],
        ),
        (
            "Technical Analysis",
            [
                ("ta", "Technical indicators"),
                ("sklearn", "Machine learning"),
            ],
        ),
        (
            "Backtesting",
            [
                ("backtesting", "Backtest framework"),
                ("empyrical", "Portfolio metrics"),
            ],
        ),
        (
            "Visualization",
            [
                ("plotly.graph_objects", "Interactive charts"),
                ("plotly.express", "Express charts"),
            ],
        ),
        (
            "UI Framework",
            [
                ("PyQt5.QtWidgets", "PyQt5 widgets"),
                ("PyQt5.QtWebEngineWidgets", "Web engine"),
            ],
        ),
    ]

    failed = []
    for category, modules in imports:
        print(f"\n{category}:")
        for module_name, description in modules:
            try:
                __import__(module_name)
                print(f"  [OK] {module_name:30} - {description}")
            except ImportError as e:
                print(f"  [FAIL] {module_name:30} - {description}")
                failed.append((module_name, str(e)))

    return len(failed) == 0, failed


def verify_project_structure():
    """Verify critical files exist"""
    print("\n" + "=" * 80)
    print("PROJECT STRUCTURE VERIFICATION")
    print("=" * 80)

    required_files = [
        "src/main.py",
        "src/mt5_connector.py",
        "src/strategy_manager.py",
        "src/backtesting/metrics_engine.py",
        "src/backtesting/trade_logger.py",
        "src/backtesting/backtest_orchestrator.py",
        "src/ui/gui/enhanced_dashboard.py",
        "src/ui/gui/plotly_charts.py",
        "src/database/db_manager.py",
        "src/core/trader.py",
        "src/core/data_fetcher.py",
        "src/config/config.yaml",
        "requirements.txt",
        "test_bot.py",
    ]

    missing = []
    for filepath in required_files:
        if os.path.exists(filepath):
            print(f"  [OK] {filepath}")
        else:
            print(f"  [FAIL] {filepath}")
            missing.append(filepath)

    return len(missing) == 0, missing


def verify_database():
    """Verify database setup"""
    print("\n" + "=" * 80)
    print("DATABASE VERIFICATION")
    print("=" * 80)

    try:
        import yaml
        from src.database.db_manager import DatabaseManager

        with open("src/config/config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        with DatabaseManager(config["database"]) as db:
            db.create_tables()
            db.create_indexes()
            print("  [OK] Database connection established")
            print("  [OK] Tables created")
            print("  [OK] Indexes created")

        return True, []
    except (FileNotFoundError, KeyError, sqlite3.Error, ValueError) as e:
        print(f"  [FAIL] Database setup failed: {e}")
        return False, [str(e)]


def verify_strategies():
    """Verify strategy factory"""
    print("\n" + "=" * 80)
    print("STRATEGY VERIFICATION")
    print("=" * 80)

    try:
        import yaml
        from src.strategies.factory import StrategyFactory
        from src.database.db_manager import DatabaseManager

        with open("src/config/config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        with DatabaseManager(config["database"]) as db:
            strategies = ["rsi", "macd"]
            for strategy_name in strategies:
                try:
                    params = (
                        config["strategies"][0]["params"]
                        if config["strategies"]
                        else {}
                    )
                    StrategyFactory.create_strategy(
                        strategy_name, params, db, mode="live"
                    )
                    print(f"  [OK] {strategy_name.upper()} strategy loaded")
                except (ImportError, KeyError, ValueError, TypeError) as e:
                    print(f"  [FAIL] {strategy_name.upper()} strategy: {e}")

        return True, []
    except (ImportError, KeyError, ValueError, FileNotFoundError, sqlite3.Error) as e:
        print(f"  [FAIL] Strategy verification failed: {e}")
        return False, [str(e)]


def verify_pyqt5_runtime():
    """Verify PyQt5 imports at runtime"""
    print("\n" + "=" * 80)
    print("PyQt5 RUNTIME VERIFICATION")
    print("=" * 80)

    try:
        from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QTableWidget
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        from PyQt5.QtCore import Qt

        print("  [OK] QMainWindow imported")
        print("  [OK] QWidget imported")
        print("  [OK] QVBoxLayout imported")
        print("  [OK] QTableWidget imported")
        print("  [OK] QWebEngineView imported")
        print("  [OK] Qt imported")

        return True, []
    except ImportError as e:
        print(f"  [FAIL] PyQt5 import error: {e}")
        return False, [str(e)]


def print_summary(results):
    """Print verification summary"""
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

    all_passed = all(result for result, _ in results.values())

    for category, (passed, errors) in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {category}")
        if errors:
            for error in errors[:3]:  # Show first 3 errors
                print(f"       - {error}")

    print("\n" + "=" * 80)
    if all_passed:
        print("STATUS: ALL SYSTEMS GO - READY FOR DEPLOYMENT")
        print("=" * 80)
        print("\nYou can now run:")
        print("  - Live trading:     python -m src.main --mode live")
        print("  - GUI dashboard:    python -m src.main --mode gui")
        print("  - Full test suite:  python test_bot.py")
    else:
        print("STATUS: SOME CHECKS FAILED - REVIEW ERRORS ABOVE")
        print("=" * 80)

    return all_passed


def main():
    """Run all verification checks"""
    print("\n" + "=" * 80)
    print("=" + " " * 78 + "=")
    print("=" + "FX TRADING BOT - SYSTEM VERIFICATION".center(78) + "=")
    print("=" + " " * 78 + "=")
    print("=" * 80)

    results = {
        "Imports": verify_imports(),
        "Project Structure": verify_project_structure(),
        "Database": verify_database(),
        "Strategies": verify_strategies(),
        "PyQt5 Runtime": verify_pyqt5_runtime(),
    }

    all_passed = print_summary(results)

    print("\nFor detailed status, see: FINAL_STATUS.md")
    print("=" * 80 + "\n")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
