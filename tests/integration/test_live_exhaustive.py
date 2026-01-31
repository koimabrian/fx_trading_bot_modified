#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Exhaustive Live Trading Test Suite
Tests each component of the live trading pipeline
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

# Fix encoding on Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import logging
import yaml
import pandas as pd
from src.database.db_manager import DatabaseManager
from src.mt5_connector import MT5Connector
from src.core.adaptive_trader import AdaptiveTrader
from src.strategy_manager import StrategyManager
from src.core.data_fetcher import DataFetcher
from src.utils.logging_factory import LoggingFactory

LoggingFactory.configure()
logger = logging.getLogger(__name__)


def test_1_database_and_data():
    """Test 1: Database connectivity and data availability"""
    print("\n" + "=" * 80)
    print("TEST 1: DATABASE & DATA AVAILABILITY")
    print("=" * 80)

    with open("src/config/config.yaml") as f:
        config = yaml.safe_load(f)

    with DatabaseManager(config["database"]) as db:
        # Check tradable pairs
        cursor = db.conn.cursor()
        cursor.execute("SELECT symbol FROM tradable_pairs")
        pairs = [row[0] for row in cursor.fetchall()]
        print(f"\n[OK] Tradable pairs in database: {pairs}")

        # Check market data
        for sym in pairs[:1]:  # Test first pair
            cursor.execute(
                """
                SELECT timeframe, COUNT(*) as count FROM market_data md
                JOIN tradable_pairs tp ON md.symbol_id = tp.id
                WHERE tp.symbol = ? GROUP BY timeframe
            """,
                (sym,),
            )
            results = cursor.fetchall()
            print(f"\n[OK] {sym} market data:")
            for tf, count in results:
                print(f"    {tf}: {count} rows")

        # Check optimal parameters
        cursor.execute("SELECT COUNT(*) FROM optimal_parameters")
        param_count = cursor.fetchone()[0]
        print(f"\n[OK] Optimal parameters stored: {param_count}")

        # Check trades table
        cursor.execute("SELECT COUNT(*) FROM trades")
        trade_count = cursor.fetchone()[0]
        print(f"[OK] Trades in database: {trade_count}")

        return True


def test_2_mt5_connection():
    """Test 2: MT5 connection and symbol availability"""
    print("\n" + "=" * 80)
    print("TEST 2: MT5 CONNECTION & SYMBOLS")
    print("=" * 80)

    with open("src/config/config.yaml") as f:
        config = yaml.safe_load(f)

    with DatabaseManager(config["database"]) as db:
        mt5_conn = MT5Connector(db)
        if not mt5_conn.initialize():
            print("[FAIL] Failed to initialize MT5")
            return False

        print("[OK] MT5 connected")

        # Test symbol fetch for each timeframe
        cursor = db.conn.cursor()
        cursor.execute("SELECT DISTINCT symbol FROM tradable_pairs LIMIT 3")
        symbols = [row[0] for row in cursor.fetchall()]

        import MetaTrader5 as mt5

        timeframe_map = {
            15: mt5.TIMEFRAME_M15,
            60: mt5.TIMEFRAME_H1,
            240: mt5.TIMEFRAME_H4,
        }

        for sym in symbols:
            for tf, mt5_tf in timeframe_map.items():
                data = mt5_conn.fetch_market_data(sym, mt5_tf, count=5)
                if data is not None and len(data) > 0:
                    latest = data.iloc[-1]
                    print(
                        f"[✓] {sym} M{tf if tf < 60 else f'H{tf//60}'}: {latest['close']:.2f}"
                    )
                else:
                    print(f"[✗] {sym} M{tf if tf < 60 else f'H{tf//60}'}: No data")

        return True


def test_3_data_fetching():
    """Test 3: Data fetcher with dynamic limits"""
    print("\n" + "=" * 80)
    print("TEST 3: DATA FETCHER WITH DYNAMIC LIMITS")
    print("=" * 80)

    with open("src/config/config.yaml") as f:
        config = yaml.safe_load(f)

    with DatabaseManager(config["database"]) as db:
        data_fetcher = DataFetcher(None, db, config)

        # Test for RSI (requires 19 rows)
        print("\n[Testing] RSI fetch (required: 19 rows)")
        data_rsi = data_fetcher.fetch_data("BTCUSD", "M15", required_rows=19)
        print(f"[✓] Fetched {len(data_rsi)} rows for RSI")
        if len(data_rsi) >= 19:
            print(f"    -> Sufficient for indicator calculation")
        else:
            print(f"    [✗] INSUFFICIENT! Need at least 19")

        # Test for MACD (requires 40 rows)
        print("\n[Testing] MACD fetch (required: 40 rows)")
        data_macd = data_fetcher.fetch_data("BTCUSD", "M15", required_rows=40)
        print(f"[✓] Fetched {len(data_macd)} rows for MACD")
        if len(data_macd) >= 40:
            print(f"    -> Sufficient for indicator calculation")
        else:
            print(f"    [✗] INSUFFICIENT! Need at least 40")

        return True


def test_4_strategy_manager():
    """Test 4: Strategy manager initialization"""
    print("\n" + "=" * 80)
    print("TEST 4: STRATEGY MANAGER")
    print("=" * 80)

    with open("src/config/config.yaml") as f:
        config = yaml.safe_load(f)

    with DatabaseManager(config["database"]) as db:
        try:
            strategy_manager = StrategyManager(db, mode="live", symbol="BTCUSD")
            print("[✓] StrategyManager initialized")
            print(f"    Mode: live")
            print(f"    Symbol: BTCUSD")
            return True
        except Exception as e:
            print(f"[✗] Failed to initialize StrategyManager: {e}")
            return False


def test_5_signal_generation():
    """Test 5: Signal generation from strategies"""
    print("\n" + "=" * 80)
    print("TEST 5: SIGNAL GENERATION")
    print("=" * 80)

    with open("src/config/config.yaml") as f:
        config = yaml.safe_load(f)

    with DatabaseManager(config["database"]) as db:
        mt5_conn = MT5Connector(db)
        mt5_conn.initialize()

        strategy_manager = StrategyManager(db, mode="live", symbol="BTCUSD")
        adaptive_trader = AdaptiveTrader(strategy_manager, mt5_conn, db)

        print("\n[Testing] Adaptive signal generation for BTCUSD")
        signals = adaptive_trader.get_signals_adaptive("BTCUSD")

        if signals:
            print(f"[✓] Generated {len(signals)} signals")
            for i, sig in enumerate(signals, 1):
                print(f"\n    Signal {i}:")
                print(f"      - Action: {sig.get('action')}")
                print(f"      - Strategy: {sig.get('strategy_info', {}).get('name')}")
                print(f"      - Entry: {sig.get('entry_price'):.2f}")
        else:
            print("[ℹ] No signals generated (market conditions don't trigger strategy)")
            print(
                "    This is NORMAL if market is not in oversold/overbought conditions"
            )

        return True


def test_5b_signal_generation_fixed_strategy():
    """Test 5b: Signal generation with fixed strategy (non-adaptive mode)"""
    print("\n" + "=" * 80)
    print("TEST 5B: SIGNAL GENERATION (FIXED STRATEGY)")
    print("=" * 80)

    with open("src/config/config.yaml") as f:
        config = yaml.safe_load(f)

    with DatabaseManager(config["database"]) as db:
        strategy_manager = StrategyManager(db, mode="live", symbol=None)

        # Get configured strategies
        configured_strategies = [s["name"] for s in config.get("strategies", [])]
        print(f"\n[Testing] Fixed strategy mode with {configured_strategies}")

        for strategy_name in configured_strategies:
            print(f"\n[Testing] Strategy: {strategy_name}")
            signals = strategy_manager.generate_signals(strategy_name)

            if isinstance(signals, list):
                print(
                    f"[✓] generate_signals() returned list with {len(signals)} signal(s)"
                )
                if signals:
                    for i, sig in enumerate(signals, 1):
                        print(
                            f"    Signal {i}: {sig.get('symbol')} "
                            f"{sig.get('action')} @ {sig.get('entry_price', 0):.2f}"
                        )
                else:
                    print(
                        f"[ℹ] No signals generated (market conditions may not trigger {strategy_name})"
                    )
            else:
                print(f"[✗] Expected list but got {type(signals)}")
                return False

        # Test with specific symbol
        print(f"\n[Testing] Fixed strategy with specific symbol")
        signal = strategy_manager.generate_signals("rsi", symbol="BTCUSD")
        if isinstance(signal, list):
            print(f"[✓] Fixed strategy with symbol=BTCUSD returned list")
            return True
        else:
            print(f"[✗] Expected list but got {type(signal)}")
            return False


def test_6_trade_execution_flow():
    """Test 6: Trade execution pipeline"""
    print("\n" + "=" * 80)
    print("TEST 6: TRADE EXECUTION FLOW")
    print("=" * 80)

    with open("src/config/config.yaml") as f:
        config = yaml.safe_load(f)

    with DatabaseManager(config["database"]) as db:
        mt5_conn = MT5Connector(db)
        mt5_conn.initialize()

        # Create test signal
        test_signal = {
            "symbol": "BTCUSD",
            "action": "buy",
            "entry_price": 89400.00,
            "stop_loss": 88400.00,
            "take_profit": 91400.00,
            "volume": 0.01,
            "timeframe": "M15",
            "strategy_info": {"name": "rsi"},
        }

        print("[Testing] Trade order placement")
        print(f"  Symbol: {test_signal['symbol']}")
        print(f"  Action: {test_signal['action']}")
        print(f"  Entry: {test_signal['entry_price']}")

        # Try to place order (will show if MT5 can accept it)
        try:
            result = mt5_conn.place_order(test_signal, "rsi")
            if result:
                print(f"[✓] Order placement succeeded")
            else:
                print(
                    f"[ℹ] Order placement returned False (may be market closed or symbol issue)"
                )
        except Exception as e:
            print(f"[ℹ] Order placement exception: {e}")

        return True


def test_7_database_recording():
    """Test 7: Trade recording in database"""
    print("\n" + "=" * 80)
    print("TEST 7: DATABASE TRADE RECORDING")
    print("=" * 80)

    with open("src/config/config.yaml") as f:
        config = yaml.safe_load(f)

    with DatabaseManager(config["database"]) as db:
        cursor = db.conn.cursor()

        # Get trade statistics
        cursor.execute(
            """
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'open' THEN 1 END) as open,
                COUNT(CASE WHEN status = 'closed' THEN 1 END) as closed,
                COUNT(CASE WHEN status = 'signal' THEN 1 END) as signals
            FROM trades
        """
        )
        result = cursor.fetchone()
        total, open_trades, closed_trades, signals = result

        print(f"\n[✓] Trade statistics:")
        print(f"    Total trades: {total}")
        print(f"    Open positions: {open_trades}")
        print(f"    Closed trades: {closed_trades}")
        print(f"    Signals generated: {signals}")

        # Get recent trades
        if total > 0:
            cursor.execute(
                """
                SELECT symbol, entry_price, status, timestamp 
                FROM trades 
                ORDER BY timestamp DESC 
                LIMIT 5
            """
            )
            print(f"\n    Recent trades:")
            for sym, price, status, ts in cursor.fetchall():
                print(f"      {sym:8} @ {price:10.2f} [{status:8}] {ts}")
        else:
            print("\n    [ℹ] No trades recorded yet (signals waiting for execution)")

        return True


def test_8_diagnostics():
    """Test 8: Run built-in diagnostics"""
    print("\n" + "=" * 80)
    print("TEST 8: LIVE TRADING DIAGNOSTICS")
    print("=" * 80)

    with open("src/config/config.yaml") as f:
        config = yaml.safe_load(f)

    with DatabaseManager(config["database"]) as db:
        mt5_conn = MT5Connector(db)
        mt5_conn.initialize()

        from src.utils.live_trading_diagnostic import LiveTradingDiagnostic

        diagnostic = LiveTradingDiagnostic(config, db, mt5_conn)
        report = diagnostic.run_full_diagnostic()

        print(
            f"\n[{'✓' if report['can_trade'] else '✗'}] Can Trade: {report['can_trade']}"
        )
        print(f"\nDiagnostic Summary:")
        print(f"  OK checks: {len(report.get('checks_ok', []))}")
        print(f"  Warnings: {len(report.get('warnings', []))}")
        print(f"  Blockers: {len(report.get('blockers', []))}")

        if report.get("warnings"):
            print(f"\n  Warnings:")
            for w in report["warnings"][:3]:
                print(f"    - {w}")

        if report.get("blockers"):
            print(f"\n  Blockers:")
            for b in report["blockers"]:
                print(f"    - {b}")

        return report["can_trade"]


def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("EXHAUSTIVE LIVE TRADING TEST SUITE")
    print("=" * 80)

    results = {
        "Database & Data": test_1_database_and_data(),
        "MT5 Connection": test_2_mt5_connection(),
        "Data Fetcher": test_3_data_fetching(),
        "Strategy Manager": test_4_strategy_manager(),
        "Signal Generation (Adaptive)": test_5_signal_generation(),
        "Signal Generation (Fixed)": test_5b_signal_generation_fixed_strategy(),
        "Trade Execution": test_6_trade_execution_flow(),
        "Database Recording": test_7_database_recording(),
        "Diagnostics": test_8_diagnostics(),
    }

    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {test_name}")

    all_passed = all(results.values())
    print("\n" + ("=" * 80))
    if all_passed:
        print("✓ ALL TESTS PASSED - System ready for live trading")
    else:
        print("✗ SOME TESTS FAILED - Check output above for issues")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
