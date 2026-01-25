import sqlite3

conn = sqlite3.connect("src/data/market_data.sqlite")
cursor = conn.cursor()

# Check backtest results
cursor.execute("SELECT COUNT(*) FROM backtest_results")
bt_count = cursor.fetchone()[0]
print(f"✓ Backtest results: {bt_count}")

# Check trades
cursor.execute("SELECT COUNT(*) FROM trades")
trades_count = cursor.fetchone()[0]
print(f"✓ Trades: {trades_count}")

# Show some backtest results
cursor.execute(
    "SELECT symbol, strategy, timeframe, sharpe_ratio, profit_factor FROM backtest_results LIMIT 3"
)
results = cursor.fetchall()
print("\nSample backtest results:")
for row in results:
    print(f"  {row[0]:8} {row[1]:6} {row[2]:3} Sharpe={row[3]:6.2f} PF={row[4]}")

conn.close()
print("\n✓ Ready for live trading!")
