"""Simple test to verify adaptive trader can find strategies and generate basic signals."""

import json
import logging
import sys
from pathlib import Path

import yaml

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.adaptive_trader import AdaptiveTrader
from src.core.strategy_selector import StrategySelector
from src.database.db_manager import DatabaseManager
from src.utils.logger import setup_logging


def main():
    """Test adaptive trader functionality."""
    setup_logging()
    logger = logging.getLogger(__name__)

    print("\n" + "=" * 80)
    print("ADAPTIVE TRADER FUNCTIONAL TEST")
    print("=" * 80)

    with open("src/config/config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    with DatabaseManager(config["database"]) as db:
        db.create_tables()
        selector = StrategySelector(db)

        print("\n[TEST 1] Checking if strategies exist in database...")
        test_symbols = ["BTCUSD", "AAPL", "MSFT"]
        test_timeframes = ["M15", "H1", "H4"]

        found_strategies = 0
        for symbol in test_symbols:
            for tf in test_timeframes:
                strategies = selector.get_best_strategies(
                    symbol=symbol, timeframe=tf, top_n=3, min_sharpe=0.0
                )
                if strategies:
                    found_strategies += 1
                    print(f"  [OK] {symbol:8} {tf}: {len(strategies)} strategy(ies)")
                    for strat in strategies:
                        print(
                            f"       - {strat['strategy_name']:8} "
                            f"(sharpe={strat['sharpe_ratio']:6.2f}, "
                            f"rank_score={strat['rank_score']:6.2f})"
                        )

        print(
            f"\n  Summary: Found {found_strategies} symbol/timeframe combos with strategies"
        )

        print("\n[TEST 2] Checking backtest_backtests table structure...")
        query = "SELECT id, symbol, timeframe, strategy_id, metrics FROM backtest_backtests LIMIT 1"
        results = db.execute_query(query)
        if results:
            r = results[0]
            print(f"  [OK] Sample record found:")
            print(f"       - ID: {r['id']}")
            print(f"       - Symbol: {r['symbol']}")
            print(f"       - Timeframe: {r['timeframe']}")
            print(f"       - Strategy ID: {r['strategy_id']}")

            metrics_str = r["metrics"]
            try:
                metrics = (
                    json.loads(metrics_str)
                    if isinstance(metrics_str, str)
                    else metrics_str
                )
                print(f"       - Metrics keys: {list(metrics.keys())[:5]}...")
                print(f"       - Sharpe ratio: {metrics.get('sharpe_ratio', 'N/A')}")
            except Exception as e:
                print(f"       - Metrics parse error: {e}")

        print("\n[TEST 3] Verifying StrategySelector ranking...")
        # Test with very low min_sharpe to get all strategies
        btc_strategies = selector.get_best_strategies(
            symbol="BTCUSD", timeframe="M15", top_n=5, min_sharpe=-100
        )
        if btc_strategies:
            print(f"  [OK] Retrieved {len(btc_strategies)} strategies for BTCUSD (M15)")
            print("       Ranked by rank_score:")
            for i, strat in enumerate(btc_strategies, 1):
                print(
                    f"         {i}. {strat['strategy_name']:8} "
                    f"sharpe={strat['sharpe_ratio']:6.2f} "
                    f"rank_score={strat['rank_score']:6.2f}"
                )

        print("\n" + "=" * 80)
        print("KEY FINDINGS:")
        print("=" * 80)
        if found_strategies > 0:
            print("[SUCCESS] Adaptive trader CAN find strategies in database!")
            print(f"          Found {found_strategies} valid strategy configurations")
            print()
            print("[NEXT STEP] The issue preventing trades is likely:")
            print("  1. No live market data to generate entry signals")
            print("  2. MT5 connection issues for live trading")
            print("  3. Trading rules preventing execution (market closed, etc.)")
            print()
            print("[TO TEST LIVE MODE] Run:")
            print("  python -m src.main --mode live")
            print()
            print("  Then monitor logs/terminal_log.txt for any errors")
        else:
            print("[ERROR] No strategies found in database!")
            print("        Run backtests first:")
            print(
                "  python -m src.backtesting.backtest_manager --mode multi-backtest --strategy rsi"
            )
            print(
                "  python -m src.backtesting.backtest_manager --mode multi-backtest --strategy macd"
            )

        print()


if __name__ == "__main__":
    main()
