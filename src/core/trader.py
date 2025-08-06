# fx_trading_bot/src/core/trader.py
# Purpose: Executes trades based on strategy signals
import logging

class Trader:
    def __init__(self, strategy_manager, mt5_connector):
        self.strategy_manager = strategy_manager
        self.mt5_connector = mt5_connector
        self.logger = logging.getLogger(__name__)

    def execute_trades(self, strategy_name=None):
        """Execute trades based on signals from strategy manager"""
        try:
            signals = self.strategy_manager.generate_signals(strategy_name)
            for signal in signals:
                self.logger.debug(f"Processing signal: {signal}")
                if self.mt5_connector.place_order(signal, strategy_name or signal.get('strategy', 'unknown')):
                    self.logger.info(f"Trade executed for {signal['symbol']}: {signal['action']}")
                else:
                    self.logger.error(f"Failed to execute trade for {signal['symbol']}")
        except Exception as e:
            self.logger.error(f"Error executing trades: {e}")