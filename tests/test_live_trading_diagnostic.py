"""Test to diagnose why no trades are being opened in live mode."""

import logging
import sys
from pathlib import Path

import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.adaptive_trader import AdaptiveTrader
from src.core.strategy_selector import StrategySelector
from src.database.db_manager import DatabaseManager
from src.mt5_connector import MT5Connector
from src.strategy_manager import StrategyManager
from src.utils.logger import setup_logging


def test_mt5_connection():
    """Test MT5 connection."""
    print("\n[TEST 1] MT5 Connection Status")
    print("-" * 60)

    with open("src/config/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    with DatabaseManager(config["database"]) as db:
        db.create_tables()
        mt5_conn = MT5Connector(db)

        if mt5_conn.initialize():
            print("[OK] MT5 connection initialized successfully")
            try:
                import MetaTrader5 as mt5

                mt5.shutdown()
            except:
                pass
            return True
        else:
            print("[FAIL] MT5 connection failed")
            print("       Check:")
            print("       - MT5 terminal is running on this machine")
            print("       - Credentials in config.yaml are correct")
            print("       - Symbol names match MT5 (case-sensitive)")
            return False


def test_data_availability():
    """Check if market data exists for adaptive trading."""
    print("\n[TEST 2] Market Data Availability")
    print("-" * 60)

    with open("src/config/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    with DatabaseManager(config["database"]) as db:
        db.create_tables()

        # Check market_data table
        query = "SELECT COUNT(*) as cnt FROM market_data"
        cursor = db.execute_query(query)
        result = cursor.fetchall()
        count = result[0][0] if result else 0

        if count > 0:
            print(f"[OK] Found {count} market data rows")

            # Check which symbols have data
            query = "SELECT DISTINCT tp.symbol, COUNT(*) as cnt FROM market_data md JOIN tradable_pairs tp ON md.symbol_id = tp.id GROUP BY tp.symbol"
            cursor = db.execute_query(query)
            results = cursor.fetchall()
            print("    Symbols with data:")
            for r in results[:10]:
                symbol = r[0]
                cnt = r[1]
                print(f"      - {symbol:8}: {cnt:5} rows")
            return True
        else:
            print("[FAIL] No market data in database")
            print("       Run:")
            print("       python -m src.main --mode sync")
            return False


def test_trading_rules():
    """Test if trading rules allow execution."""
    print("\n[TEST 3] Trading Rules (Market Hours Check)")
    print("-" * 60)

    from src.utils.trading_rules import TradingRules

    rules = TradingRules()
    test_symbols = ["BTCUSD", "EURUSD", "AAPL"]

    can_trade_any = False
    for symbol in test_symbols:
        can_trade = rules.can_trade(symbol)
        status = "[OK]" if can_trade else "[BLOCKED]"
        print(
            f"    {status} {symbol:8}: {'Can trade' if can_trade else 'Market closed or weekend'}"
        )
        if can_trade:
            can_trade_any = True

    if not can_trade_any:
        print("\n    [HINT] All symbols blocked because it's outside market hours")
        print("           Live trading only works during market hours")
        print("           (Forex: Mon-Fri, Stocks: US hours, Crypto: 24/7)")

    return can_trade_any


def test_strategy_loading():
    """Test if strategies can be loaded and used."""
    print("\n[TEST 4] Strategy Loading & Signal Generation")
    print("-" * 60)

    with open("src/config/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    setup_logging()

    with DatabaseManager(config["database"]) as db:
        db.create_tables()

        strategy_manager = StrategyManager(db, mode="live")
        selector = StrategySelector(db)

        # Try to get strategies for BTCUSD M15
        strategies = selector.get_best_strategies(
            symbol="BTCUSD", timeframe="M15", top_n=1, min_sharpe=0.0
        )

        if strategies:
            strat = strategies[0]
            print(f"[OK] Found strategy: {strat['strategy_name']}")
            print(f"    Sharpe: {strat['sharpe_ratio']:.2f}")
            print(f"    Rank score: {strat['rank_score']:.2f}")

            # Try to load strategy instance
            try:
                from src.strategies.factory import StrategyFactory

                strategy = StrategyFactory.create_strategy(
                    strat["strategy_name"],
                    config["strategies"][0]["params"],
                    db,
                    mode="live",
                )
                print(f"[OK] Strategy instance created successfully")
                return True
            except Exception as e:
                print(f"[FAIL] Could not create strategy instance: {e}")
                return False
        else:
            print("[FAIL] No strategies found")
            return False


def main():
    """Run all diagnostic tests."""
    print("\n" + "=" * 80)
    print("LIVE TRADING DIAGNOSTIC TEST")
    print("=" * 80)
    print("\nThis test checks why trades aren't being opened in adaptive trader")

    results = {
        "MT5 Connection": test_mt5_connection(),
        "Market Data": test_data_availability(),
        "Trading Rules": test_trading_rules(),
        "Strategy Loading": test_strategy_loading(),
    }

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {test_name}")

    print(f"\n  Passed: {passed}/{total}")

    if passed == total:
        print("\n[SUCCESS] All checks passed!")
        print("\nTo troubleshoot why trades aren't opening:")
        print("  1. Check logs/terminal_log.txt for error messages")
        print("  2. Run: python -m src.main --mode live")
        print("  3. Monitor the output for 'Executing adaptive trade' messages")
    else:
        print("\n[ACTION REQUIRED]")
        if not results["MT5 Connection"]:
            print("  - Start MT5 terminal and verify connection")
        if not results["Market Data"]:
            print("  - Run data sync: python -m src.main --mode sync")
        if not results["Trading Rules"]:
            print("  - Try again during market hours for that instrument")
        if not results["Strategy Loading"]:
            print("  - Run backtests to populate strategy database")

    print()


if __name__ == "__main__":
    main()
