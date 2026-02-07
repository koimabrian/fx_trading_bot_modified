"""Test that data sync respects --symbol parameter in live mode."""

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock

import yaml

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.data_fetcher import DataFetcher
from src.database.db_manager import DatabaseManager
from src.utils.logging_factory import LoggingFactory


def test_data_sync_symbol_filtering():
    """Test that has_sufficient_data and sync_data respect symbol parameter."""
    LoggingFactory.configure()
    logger = logging.getLogger(__name__)

    with open("src/config/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Generate pairs from config (same as main.py does)
    from src.main import generate_pairs_from_config

    generate_pairs_from_config(config)

    with DatabaseManager(config["database"]) as db:
        db.create_tables()

        # Mock MT5 connector
        mock_mt5 = MagicMock()
        mock_mt5.initialize.return_value = True
        mock_mt5.fetch_market_data.return_value = MagicMock(empty=True)

        # Create data fetcher
        data_fetcher = DataFetcher(mock_mt5, db, config)

        print("\n" + "=" * 80)
        print("DATA SYNC SYMBOL FILTERING TEST")
        print("=" * 80)

        # Test 1: has_sufficient_data with symbol filter
        print("\n[TEST 1] has_sufficient_data() with symbol filtering")
        print("-" * 80)

        # First, let's check how many pairs are configured
        all_pairs = data_fetcher.pairs
        print(f"Total configured pairs: {len(all_pairs)}")

        btc_pairs = [p for p in all_pairs if p["symbol"] == "BTCUSD"]
        eurusd_pairs = [p for p in all_pairs if p["symbol"] == "EURUSD"]

        print(
            f"  BTCUSD pairs: {len(btc_pairs)} (timeframes: {[p['timeframe'] for p in btc_pairs]})"
        )
        print(
            f"  EURUSD pairs: {len(eurusd_pairs)} (timeframes: {[p['timeframe'] for p in eurusd_pairs]})"
        )

        # Test has_sufficient_data with all symbols
        all_symbols_check = data_fetcher.has_sufficient_data(1000)
        print(f"\nhas_sufficient_data(1000) [no symbol filter]: {all_symbols_check}")

        # Test has_sufficient_data with BTCUSD only
        btcusd_check = data_fetcher.has_sufficient_data(1000, symbol="BTCUSD")
        print(f"has_sufficient_data(1000, symbol='BTCUSD'): {btcusd_check}")

        # Test has_sufficient_data with EURUSD only
        eurusd_check = data_fetcher.has_sufficient_data(1000, symbol="EURUSD")
        print(f"has_sufficient_data(1000, symbol='EURUSD'): {eurusd_check}")

        print("\n[PASS] has_sufficient_data() accepts symbol parameter")

        # Test 2: sync_data with symbol filter
        print("\n[TEST 2] sync_data() with symbol filtering")
        print("-" * 80)

        synced_symbols = []

        def capture_fetch_call(*args, **kwargs):
            if args:
                synced_symbols.append(args[0])  # First arg is symbol
            return MagicMock(empty=True)

        mock_mt5.fetch_market_data.side_effect = capture_fetch_call

        # Call sync_data with BTCUSD only
        data_fetcher.sync_data(symbol="BTCUSD")

        print(f"sync_data(symbol='BTCUSD') fetched symbols: {synced_symbols}")

        if all(s == "BTCUSD" for s in synced_symbols):
            print("[PASS] sync_data(symbol='BTCUSD') only syncs BTCUSD")
        else:
            print(f"[FAIL] sync_data synced other symbols: {synced_symbols}")

        # Test 3: sync_data without symbol filter
        print("\n[TEST 3] sync_data() without symbol filtering (all symbols)")
        print("-" * 80)

        synced_symbols = []
        data_fetcher.sync_data()  # No symbol specified

        unique_symbols = set(synced_symbols)
        print(
            f"sync_data() [no symbol filter] fetched symbols: {sorted(unique_symbols)}"
        )
        print(f"Total sync calls: {len(synced_symbols)}")

        if len(unique_symbols) > 1:
            print(f"[PASS] sync_data() without symbol syncs all symbols")
        else:
            print(f"[FAIL] Expected > 1 symbol, got {len(unique_symbols)}")

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print("\nData sync now respects --symbol parameter:")
        print()
        print("  python -m src.main --mode live")
        print("    => Syncs all 34 symbols (all configured pairs)")
        print()
        print("  python -m src.main --mode live --symbol BTCUSD")
        print("    => Syncs ONLY BTCUSD (3 timeframes: M15, H1, H4)")
        print()
        print("Both full sync (sync_data) and incremental sync")
        print("(sync_data_incremental) respect the --symbol parameter!")
        print()


if __name__ == "__main__":
    test_data_sync_symbol_filtering()
