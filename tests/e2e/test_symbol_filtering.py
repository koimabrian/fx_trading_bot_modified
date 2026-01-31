"""Test that --symbol parameter correctly filters adaptive trader execution."""

import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.adaptive_trader import AdaptiveTrader
from src.database.db_manager import DatabaseManager
from src.utils.logging_factory import LoggingFactory


def test_symbol_filtering():
    """Test that execute_adaptive_trades respects symbol parameter."""
    LoggingFactory.configure()

    with open("src/config/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    with DatabaseManager(config["database"]) as db:
        db.create_tables()

        # Mock MT5 connector
        mock_mt5 = MagicMock()

        # Create strategy manager mock
        from src.strategy_manager import StrategyManager

        strategy_manager = StrategyManager(db, mode="live")

        # Create adaptive trader
        adaptive_trader = AdaptiveTrader(strategy_manager, mock_mt5, db)

        print("\n" + "=" * 80)
        print("SYMBOL FILTERING TEST")
        print("=" * 80)

        # Test 1: No symbol specified - should process all symbols
        print("\n[TEST 1] execute_adaptive_trades() with NO symbol parameter")
        print("-" * 80)

        symbols_processed = []

        def capture_trading_status(symbol):
            symbols_processed.append(symbol)

        adaptive_trader.trading_rules.log_trading_status = capture_trading_status

        # Mock to avoid actual trading
        adaptive_trader.get_signals_adaptive = MagicMock(return_value=[])

        # Call with NO symbol - should process all
        adaptive_trader.execute_adaptive_trades()

        print(f"Symbols processed: {sorted(symbols_processed)}")
        print(f"Total symbols: {len(symbols_processed)}")

        if len(symbols_processed) > 1:
            print("[PASS] All symbols processed when no --symbol specified")
        else:
            print(f"[FAIL] Expected > 1 symbol, got {len(symbols_processed)}")

        # Test 2: With specific symbol
        print("\n[TEST 2] execute_adaptive_trades(symbol='BTCUSD')")
        print("-" * 80)

        symbols_processed = []
        adaptive_trader.execute_adaptive_trades(symbol="BTCUSD")

        print(f"Symbols processed: {symbols_processed}")

        if symbols_processed == ["BTCUSD"]:
            print("[PASS] Only BTCUSD processed when --symbol BTCUSD specified")
        else:
            print(f"[FAIL] Expected ['BTCUSD'], got {symbols_processed}")

        # Test 3: With different symbol
        print("\n[TEST 3] execute_adaptive_trades(symbol='EURUSD')")
        print("-" * 80)

        symbols_processed = []
        adaptive_trader.execute_adaptive_trades(symbol="EURUSD")

        print(f"Symbols processed: {symbols_processed}")

        if symbols_processed == ["EURUSD"]:
            print("[PASS] Only EURUSD processed when --symbol EURUSD specified")
        else:
            print(f"[FAIL] Expected ['EURUSD'], got {symbols_processed}")

        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print("\nThe fix ensures that:")
        print("  python -m src.main --mode live")
        print("    → Trades ALL symbols (all_symbols list)")
        print()
        print("  python -m src.main --mode live --symbol BTCUSD")
        print("    → Trades ONLY BTCUSD (single-element list)")
        print()
        print("For Fixed Strategy Mode:")
        print("  python -m src.main --mode live --strategy rsi")
        print(
            "    → Uses Trader.execute_trades() which respects StrategyManager.symbol"
        )
        print()


if __name__ == "__main__":
    test_symbol_filtering()
