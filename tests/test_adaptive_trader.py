"""Test and debug the adaptive trader functionality."""

import logging
import sqlite3
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


def test_database_contents():
    """Check if backtest results exist in the database."""
    print("\n" + "=" * 80)
    print("STEP 1: Check Database Contents")
    print("=" * 80)

    with open("src/config/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    db_path = config["database"]["path"]
    print(f"\nDatabase path: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"\nAvailable tables: {[t[0] for t in tables]}")

        # Check backtest_backtests table
        cursor.execute("SELECT COUNT(*) FROM backtest_backtests")
        count = cursor.fetchone()[0]
        print(f"\nBacktest results in backtest_backtests: {count}")

        if count > 0:
            cursor.execute(
                "SELECT DISTINCT symbol, timeframe, COUNT(*) FROM backtest_backtests GROUP BY symbol, timeframe LIMIT 10"
            )
            results = cursor.fetchall()
            print("\nSample backtest results (symbol, timeframe, count):")
            for symbol, timeframe, cnt in results:
                print(f"  {symbol} {timeframe}: {cnt} results")

        # Check optimal_params table
        cursor.execute("SELECT COUNT(*) FROM optimal_params")
        count = cursor.fetchone()[0]
        print(f"\nStrategy parameters in optimal_params: {count}")

        if count > 0:
            cursor.execute(
                "SELECT strategy_name, symbol, timeframe, rank_score FROM optimal_params ORDER BY rank_score DESC LIMIT 10"
            )
            results = cursor.fetchall()
            print("\nTop 10 strategies by rank_score:")
            for strategy, symbol, timeframe, rank_score in results:
                print(
                    f"  {strategy:8} {symbol:8} {timeframe:4} rank_score={rank_score:.4f}"
                )

        conn.close()

    except Exception as e:
        print(f"Error checking database: {e}")


def test_strategy_selector():
    """Test the StrategySelector to see if it retrieves strategies."""
    print("\n" + "=" * 80)
    print("STEP 2: Test Strategy Selector")
    print("=" * 80)

    with open("src/config/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    with DatabaseManager(config["database"]) as db:
        db.create_tables()
        selector = StrategySelector(db)

        # Test symbols
        test_symbols = ["BTCUSD", "EURUSD", "AAPL", "MSFT"]

        for symbol in test_symbols:
            for timeframe in ["M15", "H1", "H4"]:
                strategies = selector.get_best_strategies(
                    symbol=symbol, timeframe=timeframe, top_n=3, min_sharpe=0.5
                )

                if strategies:
                    print(
                        f"\n{symbol} ({timeframe}): Found {len(strategies)} qualifying strategies"
                    )
                    for i, strat in enumerate(strategies, 1):
                        print(
                            f"  {i}. {strat['strategy_name']}: "
                            f"sharpe={strat.get('sharpe_ratio', 0):.2f}, "
                            f"rank_score={strat.get('rank_score', 0):.4f}, "
                            f"win_rate={strat.get('win_rate_pct', 0):.1f}%"
                        )
                else:
                    print(f"\n{symbol} ({timeframe}): No qualifying strategies found")


def test_adaptive_trader_signals():
    """Test if adaptive trader can generate signals."""
    print("\n" + "=" * 80)
    print("STEP 3: Test Adaptive Trader Signal Generation")
    print("=" * 80)

    setup_logging()
    logger = logging.getLogger(__name__)

    with open("src/config/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    with DatabaseManager(config["database"]) as db:
        db.create_tables()

        # Create minimal MT5 connector (no real connection needed)
        class MockMT5Connector:
            def __init__(self):
                self.logger = logging.getLogger(__name__)

        mt5_conn = MockMT5Connector()

        strategy_manager = StrategyManager(db, mode="live")
        adaptive_trader = AdaptiveTrader(strategy_manager, mt5_conn, db)

        # Test symbols
        test_symbols = ["BTCUSD", "EURUSD", "AAPL"]

        for symbol in test_symbols:
            print(f"\nTesting signal generation for {symbol}...")
            signals = adaptive_trader.get_signals_adaptive(symbol)

            if signals:
                print(f"  Generated {len(signals)} signals")
                for signal in signals[:3]:  # Show first 3
                    print(
                        f"    - {signal['action']}: "
                        f"confidence={signal.get('confidence', 0):.2f}, "
                        f"strategy={signal.get('strategy_info', {}).get('name', 'unknown')}"
                    )
            else:
                print(f"  No signals generated for {symbol}")


def main():
    """Run all tests."""
    print("\n\n")
    print("=" * 80)
    print("ADAPTIVE TRADER DEBUGGING & VERIFICATION".center(80))
    print("=" * 80)

    test_database_contents()
    test_strategy_selector()
    test_adaptive_trader_signals()

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print("\nIf no strategies were found, you need to run backtests first:")
    print(
        "  python -m src.backtesting.backtest_manager --mode multi-backtest --strategy rsi"
    )
    print(
        "  python -m src.backtesting.backtest_manager --mode multi-backtest --strategy macd"
    )
    print("\n")


if __name__ == "__main__":
    main()
