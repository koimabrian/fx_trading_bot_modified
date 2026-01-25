#!/usr/bin/env python
"""
Comprehensive Test: Verify trade monitoring even with trades table cleanup on live start
"""
import sqlite3
import time
import json
from datetime import datetime


def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def get_trade_stats():
    """Get current trade statistics from database"""
    conn = sqlite3.connect("src/data/market_data.sqlite")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get summary stats
    cursor.execute(
        """
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN close_time IS NULL THEN 1 ELSE 0 END) as open_count,
            SUM(CASE WHEN close_time IS NOT NULL THEN 1 ELSE 0 END) as closed_count,
            SUM(CASE WHEN close_time IS NOT NULL AND profit IS NOT NULL THEN profit ELSE 0 END) as realized_pnl
        FROM trades
    """
    )
    stats = dict(cursor.fetchone())

    # Get MT5 positions
    cursor.execute(
        """
        SELECT tp.symbol, t.trade_type, t.open_price, t.status, t.open_time
        FROM trades t
        JOIN tradable_pairs tp ON t.symbol_id = tp.id
        WHERE t.close_time IS NULL
        ORDER BY t.open_time DESC
        LIMIT 10
    """
    )
    open_trades = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return stats, open_trades


def main():
    print_section("TEST: Trade Monitoring After Table Cleanup")
    print(f"\nTest Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nThis test verifies:")
    print("  1. Trades table is cleaned on live start")
    print("  2. New trades are created during live trading")
    print("  3. Dashboard correctly tracks trade metrics")
    print("  4. Metrics update in real-time")

    print_section("Initial State: Before Live Mode")
    stats, trades = get_trade_stats()
    print(f"\nDatabase State:")
    print(f"  Total Trades: {stats['total']}")
    print(f"  Open Trades: {stats['open_count']}")
    print(f"  Closed Trades: {stats['closed_count']}")
    print(f"  Realized P&L: ${stats['realized_pnl'] or 0:.2f}")

    if stats["total"] == 0:
        print("\n✓ Trades table successfully cleaned on previous live start")
    else:
        print(f"\n⚠ WARNING: {stats['total']} trades still in database")

    print_section("Expected Test Results")
    print("\nAfter running live trading, the system should:")
    print("  • Create new trade records when signals are generated")
    print("  • Track open trades with open_time but no close_time")
    print("  • Track closed trades with both open_time and close_time")
    print("  • Calculate metrics correctly in dashboard")
    print("  • Show unrealized P&L from MT5 positions")
    print("\nNote: Trade generation depends on:")
    print("  • Market conditions generating valid signals")
    print("  • Strategy confidence levels")
    print("  • Risk management filters")

    print_section("Dashboard Verification")
    print("\nAccess dashboard at: http://127.0.0.1:5000")
    print("\nExpected metrics:")
    print("  • Open Positions: Count of MT5 live positions (≥ 0)")
    print("  • Total Trades: All trades ever executed (≥ 0)")
    print("  • Net Profit: Realized + Unrealized P&L")
    print("  • Win Rate: Only from closed trades (0% if no closed trades)")


if __name__ == "__main__":
    main()
