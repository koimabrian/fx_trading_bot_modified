# src/ui/cli.py
# Purpose: Command-line interface argument parsing
import argparse

def setup_parser():
    """Set up argument parser for CLI."""
    parser = argparse.ArgumentParser(description="FX Trading Bot")
    parser.add_argument('--mode', choices=['live', 'backtest', 'gui', 'sync', 'migrate', 'optimize'], default='live',
                        help='Mode to run the bot in: live, backtest, gui, sync, migrate, or optimize')
    parser.add_argument('--strategy', type=str, default=None,
                        help='Strategy to use (e.g., rsi, macd)')
    parser.add_argument('--symbol', type=str, default=None,
                        help='Symbol to trade or backtest (e.g., XAUUSD)')
    return parser