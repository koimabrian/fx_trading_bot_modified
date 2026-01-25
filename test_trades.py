import sqlite3
import time

conn = sqlite3.connect("src/data/market_data.sqlite")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 70)
print("TRADE MONITORING TEST")
print("=" * 70)

# Check trades
cursor.execute("SELECT COUNT(*) as count FROM trades")
total = cursor.fetchone()["count"]

cursor.execute("SELECT COUNT(*) as count FROM trades WHERE close_time IS NULL")
open_count = cursor.fetchone()["count"]

cursor.execute("SELECT COUNT(*) as count FROM trades WHERE close_time IS NOT NULL")
closed_count = cursor.fetchone()["count"]

print(f"\nTrades Current State:")
print(f"  Total trades: {total}")
print(f"  Open trades: {open_count}")
print(f"  Closed trades: {closed_count}")

if total > 0:
    print(f"\nTrade Details:")
    cursor.execute(
        """SELECT tp.symbol, t.trade_type, t.status, t.open_price, t.profit, t.open_time
                      FROM trades t
                      JOIN tradable_pairs tp ON t.symbol_id = tp.id
                      ORDER BY t.open_time DESC
                      LIMIT 10"""
    )
    for row in cursor.fetchall():
        print(
            f"  {row['symbol']}: {row['trade_type']:<4} | Status: {row['status']:<12} | Price: {row['open_price']:>10.2f} | P&L: {row['profit']}"
        )
else:
    print("\nNo trades found in database")

conn.close()
