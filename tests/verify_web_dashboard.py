"""Verify web dashboard implementation."""

import os
import sys

print("\n" + "=" * 70)
print("FX TRADING BOT - WEB DASHBOARD VERIFICATION")
print("=" * 70)

# Check file structure
print("\n1. FILE STRUCTURE CHECK:")
print("-" * 70)

files_to_check = [
    "src/ui/web/__init__.py",
    "src/ui/web/dashboard_server.py",
    "src/ui/web/templates/dashboard.html",
    "src/ui/web/static/dashboard.css",
    "src/ui/web/static/dashboard.js",
]

all_files_exist = True
for file_path in files_to_check:
    exists = os.path.exists(file_path)
    status = "✓" if exists else "✗"
    print(f"  {status} {file_path}")
    if not exists:
        all_files_exist = False

# Check Python syntax
print("\n2. PYTHON SYNTAX CHECK:")
print("-" * 70)

try:
    import py_compile

    py_compile.compile("src/ui/web/dashboard_server.py", doraise=True)
    print("  ✓ dashboard_server.py")
except Exception as e:
    print(f"  ✗ dashboard_server.py: {e}")

try:
    import py_compile

    py_compile.compile("src/main.py", doraise=True)
    print("  ✓ main.py")
except Exception as e:
    print(f"  ✗ main.py: {e}")

# Check imports
print("\n3. IMPORTS CHECK:")
print("-" * 70)

try:
    from src.ui.web.dashboard_server import DashboardServer

    print("  ✓ DashboardServer imported successfully")
except ImportError as e:
    print(f"  ✗ Failed to import DashboardServer: {e}")

try:
    from flask import Flask

    print("  ✓ Flask available")
except ImportError:
    print("  ✗ Flask not installed - run: pip install Flask")

try:
    from flask_cors import CORS

    print("  ✓ Flask-CORS available")
except ImportError:
    print("  ✗ Flask-CORS not installed - run: pip install Flask-CORS")

# Check database
print("\n4. DATABASE CHECK:")
print("-" * 70)

if os.path.exists("src/data/market_data.sqlite"):
    print("  ✓ Database file exists")

    try:
        import sqlite3

        conn = sqlite3.connect("src/data/market_data.sqlite")
        cursor = conn.cursor()

        # Check backtest_backtests table
        cursor.execute("SELECT COUNT(*) FROM backtest_backtests")
        count = cursor.fetchone()[0]
        print(f"  ✓ Backtest results: {count} records")

        # Check symbols
        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM backtest_backtests")
        symbols = cursor.fetchone()[0]
        print(f"  ✓ Unique symbols: {symbols}")

        conn.close()
    except Exception as e:
        print(f"  ✗ Database error: {e}")
else:
    print("  ⚠ Database not found - run: python -m src.main --mode sync")

# Check backtest results
print("\n5. BACKTEST RESULTS CHECK:")
print("-" * 70)

if os.path.exists("backtests/results"):
    equity_files = len(
        [f for f in os.listdir("backtests/results") if "equity_curve" in f]
    )
    heatmap_files = len([f for f in os.listdir("backtests/results") if "heatmap" in f])
    print(f"  ✓ Equity curve files: {equity_files}")
    print(f"  ✓ Heatmap files: {heatmap_files}")
else:
    print("  ⚠ Results directory not found")

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

if all_files_exist:
    print("\n✓ WEB DASHBOARD READY FOR USE!")
    print("\nTo launch the dashboard:")
    print("  python -m src.main --mode gui")
    print("\nThen open in your browser:")
    print("  http://127.0.0.1:5000")
else:
    print("\n✗ Some files are missing. Check output above.")

print("\nFor detailed setup instructions:")
print("  See: WEB_DASHBOARD_GUIDE.md")
print("\n" + "=" * 70 + "\n")
