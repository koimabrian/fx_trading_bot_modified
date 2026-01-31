"""Trade execution engine with risk management.

Executes trades based on strategy signals, enforces position limits,
applies trading rules, and manages MT5 order placement.
"""

import logging

import yaml

from src.utils.error_handler import ErrorHandler
from src.utils.logging_factory import LoggingFactory
from src.utils.trading_rules import TradingRules


class Trader:
    """Executes trades based on strategy signals and enforces trading rules."""

    def __init__(self, strategy_manager, mt5_connector):
        """Initialize trader with strategy manager and MT5 connector.

        Args:
            strategy_manager: StrategyManager instance for signal generation
            mt5_connector: MT5Connector instance for order placement
        """
        self.strategy_manager = strategy_manager
        self.mt5_connector = mt5_connector
        self.logger = LoggingFactory.get_logger(__name__)
        self.trading_rules = TradingRules()
        self.config = self._load_config()

    def _load_config(self):
        """Load configuration from YAML file."""
        try:
            from src.utils.config_manager import ConfigManager

            return ConfigManager.get_config()
        except Exception as e:
            ErrorHandler.handle_error(e, context="load_config")
            return {}

    def get_max_open_positions(self):
        """Get maximum allowed open positions from config.

        Returns:
            Integer maximum open positions (default 10 if not specified)
        """
        return self.config.get("risk_management", {}).get("max_positions", 10)

    def get_min_confidence(self):
        """Get minimum signal confidence from config.

        IMPROVED: Returns different thresholds based on mode
        - aggressive_mode: 0.5 (allows more trades)
        - normal_mode: 0.6 (filtered for quality)

        Returns:
            Float minimum confidence requirement (0.0 to 1.0)
        """
        live_config = self.config.get("live_trading", {})
        aggressive = live_config.get("aggressive_mode", False)

        if aggressive:
            return 0.5  # Allow more marginal signals
        else:
            return live_config.get("min_signal_confidence", 0.6)  # Standard filtering

    def get_current_position_count(self):
        """Get current number of open positions from MT5.

        Returns:
            Integer count of open positions
        """
        return self.mt5_connector.get_open_positions_count()

    def can_open_new_position(self):
        """Check if a new position can be opened based on position limits.

        Returns:
            Boolean indicating if position opening is allowed
        """
        current_positions = self.get_current_position_count()
        max_positions = self.get_max_open_positions()

        if current_positions >= max_positions:
            self.logger.warning(
                "Position limit reached: %d/%d open positions",
                current_positions,
                max_positions,
            )
            return False

        return True

    def execute_trades(self, strategy_name=None):
        """Execute trades based on signals from strategy manager.
        Respects trading rules (e.g., no forex/commodities on weekends).
        """
        try:
            # Check if position limit allows new trades
            if not self.can_open_new_position():
                self.logger.debug("Skipping trade execution: position limit reached")
                return

            signals = self.strategy_manager.generate_signals(strategy_name)
            for signal in signals:
                symbol = signal.get("symbol")

                # Check trading rules - MUST pass before any order attempt
                self.trading_rules.log_trading_status(symbol)
                can_trade = self.trading_rules.can_trade(symbol)

                if not can_trade:
                    self.logger.warning(
                        "Trade BLOCKED for %s: Market closed (weekend or non-trading hours)",
                        symbol,
                    )
                    continue  # Skip this signal entirely

                # Final verification before processing
                self.logger.debug("Processing signal: %s", signal)
                if self.mt5_connector.place_order(
                    signal, strategy_name or signal.get("strategy", "unknown")
                ):
                    self.logger.info(
                        "Trade executed for %s: %s", signal["symbol"], signal["action"]
                    )
                else:
                    self.logger.error(
                        "Failed to execute trade for %s", signal["symbol"]
                    )
        except Exception as e:
            ErrorHandler.handle_error(e, context="execute_trades")
