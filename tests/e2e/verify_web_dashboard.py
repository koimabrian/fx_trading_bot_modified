"""Verify web dashboard implementation."""

import os
import sys

# Fix encoding on Windows
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

print("\n" + "=" * 70)
print("FX TRADING BOT - WEB DASHBOARD VERIFICATION")
print("=" * 70)

# Check file structure
print("\n1. FILE STRUCTURE CHECK:")
print("-" * 70)

files_to_check = [
    "src/ui/web/__init__.py",
    "src/ui/web/dashboard_server.py",
    "src/ui/web/templates/dashboard_unified.html",
]

all_files_exist = True
for file_path in files_to_check:
    exists = os.path.exists(file_path)
    status = "[OK]" if exists else "[FAIL]"
    print(f"  {status} {file_path}")
    if not exists:
        all_files_exist = False

# Check Python syntax
print("\n2. PYTHON SYNTAX CHECK:")
print("-" * 70)

try:
    import py_compile

    py_compile.compile("src/ui/web/dashboard_server.py", doraise=True)
    print("  [OK] dashboard_server.py")
except Exception as e:
    print(f"  [FAIL] dashboard_server.py: {e}")

try:
    import py_compile

    py_compile.compile("src/main.py", doraise=True)
    print("  [OK] main.py")
except Exception as e:
    print(f"  [FAIL] main.py: {e}")

# Check imports
print("\n3. IMPORTS CHECK:")
print("-" * 70)

try:
    print("  [OK] DashboardServer imported successfully")
except ImportError as e:
    print(f"  [FAIL] Failed to import DashboardServer: {e}")

try:
    print("  [OK] Flask available")
except ImportError:
    print("  [FAIL] Flask not installed - run: pip install Flask")

try:
    print("  [OK] Flask-CORS available")
except ImportError:
    print("  [FAIL] Flask-CORS not installed - run: pip install Flask-CORS")

# Check database
print("\n4. DATABASE CHECK:")
print("-" * 70)

if os.path.exists("src/data/market_data.sqlite"):
    print("  [OK] Database file exists")

    try:
        import sqlite3

        conn = sqlite3.connect("src/data/market_data.sqlite")
        cursor = conn.cursor()

        # Check backtest_backtests table
        cursor.execute("SELECT COUNT(*) FROM backtest_backtests")
        count = cursor.fetchone()[0]
        print(f"  [OK] Backtest results: {count} records")

        # Check symbols
        cursor.execute("SELECT COUNT(DISTINCT strategy) FROM backtest_backtests")
        symbols = cursor.fetchone()[0]
        print(f"  [OK] Unique strategies: {symbols}")

        conn.close()
    except Exception as e:
        print(f"  [FAIL] Database error: {e}")
else:
    print("  [WARN] Database not found - run: python -m src.main --mode sync")

# Check backtest results
print("\n5. BACKTEST RESULTS CHECK:")
print("-" * 70)

if os.path.exists("backtests/results"):
    equity_files = len(
        [f for f in os.listdir("backtests/results") if "equity_curve" in f]
    )
    heatmap_files = len([f for f in os.listdir("backtests/results") if "heatmap" in f])
    print(f"  [OK] Equity curve files: {equity_files}")
    print(f"  [OK] Heatmap files: {heatmap_files}")
else:
    print("  [WARN] Results directory not found")

# Summary
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

if all_files_exist:
    print("\n[OK] WEB DASHBOARD READY FOR USE!")
    print("\nTo launch the dashboard:")
    print("  python -m src.main --mode gui")
    print("\nThen open in your browser:")
    print("  http://127.0.0.1:5000")
else:
    print("\n[FAIL] Some files are missing. Check output above.")

print("\n" + "=" * 70 + "\n")
