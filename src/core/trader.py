# fx_trading_bot/src/core/trader.py
# Purpose: Manage trading logic (signal generation and order placement)
import logging

class Trader:
    def __init__(self, strategy_manager, mt5_conn):
        self.strategy_manager = strategy_manager
        self.mt5_conn = mt5_conn
        self.logger = logging.getLogger(__name__)

    def execute_trades(self, strategy_name: str = None):
        """Generate signals and place orders"""
        signals = self.strategy_manager.generate_signals(strategy_name)
        for signal in signals:
            if self.mt5_conn.get_open_positions_count() >= 5:
                self.logger.warning("Max positions limit (5) reached. Skipping new order.")
                continue
            self.mt5_conn.place_order(signal, strategy_name if strategy_name else "Unknown")