# fx_trading_bot/src/core/trade_monitor.py
# Purpose: Monitor and close open positions
import logging

class TradeMonitor:
    def __init__(self, strategy_manager, mt5_conn):
        self.strategy_manager = strategy_manager
        self.mt5_conn = mt5_conn
        self.logger = logging.getLogger(__name__)

    def monitor_positions(self, strategy_name: str = None):
        """Monitor and close positions based on exit strategy"""
        self.mt5_conn.monitor_and_close_positions(strategy_name)