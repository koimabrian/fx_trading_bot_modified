#!/usr/bin/env python3
"""Test that the API fix works - verifying DataFetcher is instantiated correctly."""

import sys
import yaml

sys.path.insert(0, ".")

from src.utils.indicator_analyzer import IndicatorAnalyzer
from src.database.db_manager import DatabaseManager


def test_indicator_analyzer_instantiation():
    """Test that IndicatorAnalyzer can be instantiated with correct parameters."""
    try:
        # Load config like main.py does
        with open("src/config/config.yaml", "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)

        db = DatabaseManager(config)

        # Test 1: Instantiate with db only (should work with new signature)
        analyzer1 = IndicatorAnalyzer(db)
        print("Test 1 passed: IndicatorAnalyzer(db)")

        # Test 2: Instantiate with db and config
        analyzer2 = IndicatorAnalyzer(db, config=config)
        print("Test 2 passed: IndicatorAnalyzer(db, config=config)")

        # Test 3: Instantiate with all parameters
        analyzer3 = IndicatorAnalyzer(db, mt5_conn=None, config=config)
        print("Test 3 passed: IndicatorAnalyzer(db, mt5_conn=None, config=config)")

        # Test 4: Verify that DataFetcher was instantiated correctly
        assert analyzer1.data_fetcher is not None
        assert analyzer2.data_fetcher is not None
        assert analyzer3.data_fetcher is not None
        print("Test 4 passed: DataFetcher instances created successfully")

        print("\nAll tests passed! The API fix is working correctly.")
        return True

    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_indicator_analyzer_instantiation()
    sys.exit(0 if success else 1)
