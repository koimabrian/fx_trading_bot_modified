# fx_trading_bot/src/core/trade_monitor.py
# Purpose: Monitor and close open positions
import logging


class TradeMonitor:
    """Monitors and closes open positions based on exit strategy."""

    def __init__(self, strategy_manager, mt5_conn):
        """Initialize trade monitor.

        Args:
            strategy_manager: StrategyManager instance for exit signal generation
            mt5_conn: MT5Connector instance for position management
        """
        self.strategy_manager = strategy_manager
        self.mt5_conn = mt5_conn
        self.logger = logging.getLogger(__name__)

    def monitor_positions(self, strategy_name: str = None):
        """Monitor and close positions based on exit strategy"""
        self.mt5_conn.monitor_and_close_positions(strategy_name)
