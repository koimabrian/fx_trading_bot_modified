# fx_trading_bot/src/ui/cli.py
# Purpose: Command-line interface argument parsing
import argparse

def setup_parser():
    """Set up argument parser for CLI"""
    parser = argparse.ArgumentParser(description="FX Trading Bot")
    parser.add_argument('--mode', choices=['live', 'gui'], default='live',
                        help='Mode to run the bot in: live or gui')
    parser.add_argument('--strategy', type=str, default=None,
                        help='Strategy to use (e.g., rsi, macd)')
    return parser