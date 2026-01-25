import sqlite3
import json

conn = sqlite3.connect("src/data/market_data.sqlite")
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print("All tables:", tables)

# Check each table for data
for table in ["backtest_results", "backtest_backtests", "optimal_parameters"]:
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"\n✓ {table}: {count} rows")

        if count > 0 and table == "backtest_backtests":
            cursor.execute(
                f"SELECT strategy_id, symbol_id, timeframe, metrics FROM {table} LIMIT 2"
            )
            for row in cursor.fetchall():
                metrics = json.loads(row[3])
                print(
                    f"  Strategy={row[0]} Symbol={row[1]} TF={row[2]} Sharpe={metrics.get('sharpe_ratio', 0):.2f}"
                )
    except Exception as e:
        print(f"✗ {table}: {e}")

conn.close()
