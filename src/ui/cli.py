"""Command-line interface parser for the FX Trading Bot.

Defines argument parsing for all operational modes: init, sync, backtest,
live, gui, and test. Supports symbol and strategy filtering per mode.
"""

import argparse


def setup_parser():
    """Set up argument parser for CLI with all 6 modes.

    Returns:
        ArgumentParser configured with all operational modes and flags.
    """
    parser = argparse.ArgumentParser(
        description="FX Trading Bot - Adaptive Strategy Selection System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  init     - Initialize database and load tradable pairs from MT5
  sync     - Synchronize market data from MT5 (incremental or full)
  backtest - Run backtests with volatility filtering and parameter optimization
  live     - Real-time trading with adaptive strategy selection
  gui      - Web dashboard for monitoring (read-only)
  test     - Run comprehensive test suite

Examples:
  python -m src.main init                           # Initialize database
  python -m src.main sync --symbol EURUSD           # Sync one symbol
  python -m src.main backtest --strategy rsi        # Backtest RSI strategy
  python -m src.main live --symbol BTCUSD           # Trade one symbol
  python -m src.main gui --host 127.0.0.1 --port 5000  # Start dashboard
  python -m src.main test                           # Run tests
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["init", "sync", "backtest", "live", "gui", "test"],
        default="live",
        help="Operation mode (default: live)",
    )

    parser.add_argument(
        "--symbol",
        default=None,
        help="Specific trading symbol (e.g., BTCUSD, EURUSD). "
        "If not specified, all configured symbols are used.",
    )

    parser.add_argument(
        "--strategy",
        default=None,
        help="Specific strategy to use (e.g., rsi, macd). "
        "If not specified, adaptive selection is used.",
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help="For sync mode: perform full data refresh instead of incremental.",
    )

    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for GUI dashboard (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port for GUI dashboard (default: 5000)",
    )

    return parser
