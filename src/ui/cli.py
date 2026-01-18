# fx_trading_bot/src/ui/cli.py
# Purpose: Defines command-line interface arguments
import argparse


def setup_parser():
    """Set up argument parser for CLI"""
    parser = argparse.ArgumentParser(description="FX Trading Bot")
    parser.add_argument(
        "--mode",
        choices=["live", "gui"],
        default="live",
        help="Operation mode: live trading or GUI",
    )
    parser.add_argument(
        "--strategy", default=None, help="Specific strategy to use (e.g., rsi, macd)"
    )
    # parser.add_argument(
    #     "--symbol", default=None, help="Specific trading symbol (e.g., BTCUSD, EURUSD)"
    # )
    return parser
