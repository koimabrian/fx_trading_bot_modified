"""MetaTrader5 connection and data management.

Handles MT5 API communication, order placement, market data retrieval,
and account management. Provides context manager interface for safe
connection handling.
"""

# pylint: disable=no-member
import os
import time
from datetime import datetime

import MetaTrader5 as mt5
import pandas as pd

from src.strategies.factory import StrategyFactory
from src.utils.config_manager import ConfigManager
from src.utils.logging_factory import LoggingFactory
from src.utils.mt5_decorator import mt5_safe
from src.utils.timeframe_utils import mt5_timeframe_to_minutes


class MT5Connector:
    """Manages connection and operations with MetaTrader 5.

    Singleton pattern ensures MT5 initializes only once across the application.
    """

    _instance = None
    _initialized = False

    def __new__(cls, db):
        """Singleton pattern: return existing instance or create new one.

        Args:
            db: Database manager instance.

        Returns:
            The singleton MT5Connector instance.
        """
        if cls._instance is None:
            cls._instance = super(MT5Connector, cls).__new__(cls)
            cls._instance._init_instance(db)
        return cls._instance

    def _init_instance(self, db):
        """Initialize instance once (called only on first creation).

        Args:
            db: Database manager instance for storing trade data.
        """
        self.db = db
        self.logger = LoggingFactory.get_logger(__name__)
        # Load credentials from config.yaml or environment variables
        config = ConfigManager.get_config()
        mt5_config = config.get("mt5", {})
        self.login = int(os.getenv("MT5_LOGIN", mt5_config.get("login", 0)))
        self.password = os.getenv("MT5_PASSWORD", mt5_config.get("password", ""))
        self.server = os.getenv("MT5_SERVER", mt5_config.get("server", ""))
        self.logger.debug("MT5Connector singleton created")

    def initialize(self):
        """Initialize MT5 connection with credentials from config.

        Checks if already initialized to prevent duplicate init calls.
        Loads credentials from config.yaml or environment variables.

        Returns:
            True if successfully initialized or already connected,
            False if credentials are missing or connection fails.
        """
        # Check if already initialized
        if MT5Connector._initialized:
            self.logger.debug("MT5 already initialized, skipping duplicate init")
            return True

        if not self.login or not self.password or not self.server:
            self.logger.error(
                "MT5 credentials missing. Please update src/config/config.yaml or set MT5_LOGIN, MT5_PASSWORD, MT5_SERVER environment variables."
            )
            return False

        try:  # pylint: disable=no-member
            # Check if MT5 terminal is already running
            if mt5.terminal_info() is not None:
                self.logger.debug("MT5 terminal already connected, reusing connection")
                MT5Connector._initialized = True
                return True

            self.logger.debug(
                "Attempting MT5 connection with login=%s, server=%s",
                self.login,
                self.server,
            )
            if not mt5.initialize(
                login=self.login,
                password=self.password,
                server=self.server,
                timeout=30000,
            ):
                error_code, error_msg = mt5.last_error()
                self.logger.error(
                    "MT5 initialization failed: Error code %s, Message: %s",
                    error_code,
                    error_msg,
                )
                self.logger.info(
                    "Possible causes: MT5 terminal not running, invalid credentials, incorrect server name, or network issues."
                )
                self.logger.info(
                    "Ensure MetaTrader 5 is running, credentials are correct, and the server (e.g., Exness-MT5Trial9) is accessible."
                )
                return False
            MT5Connector._initialized = True
            self.logger.info("MT5 connection initialized successfully (singleton)")
            return True
        except (RuntimeError, OSError, ValueError) as e:
            self.logger.error("Unexpected error during MT5 initialization: %s", e)
            return False

    @mt5_safe(max_retries=3, retry_delay=1.0)
    def fetch_market_data(self, symbol, timeframe, count=1000):
        """Fetch market data from MT5 with improved error handling and logging.

        Uses mt5.copy_rates_range for more reliable fetching instead of copy_rates_from_pos.

        Args:
            symbol: Trading symbol (e.g., 'EURUSD').
            timeframe: MT5 timeframe constant (e.g., mt5.TIMEFRAME_M15).
            count: Number of candles to fetch.

        Returns:
            DataFrame with OHLCV data, or None on error.
        """
        try:
            # Handle None timeframe by using a safe default
            if timeframe is None:
                self.logger.warning(
                    "Timeframe is None for %s, using TIMEFRAME_M15 as default", symbol
                )
                timeframe = mt5.TIMEFRAME_M15

            self.logger.debug(
                "fetch_market_data: symbol=%s, timeframe=%s (type=%s), count=%d",
                symbol,
                timeframe,
                type(timeframe),
                count,
            )

            # Get current UTC time to fetch recent data
            now = time.time()

            # Calculate date range: from 'count' periods ago to now
            # Determine timeframe_minutes for date range calculation
            timeframe_minutes = mt5_timeframe_to_minutes(timeframe)

            seconds_back = count * timeframe_minutes * 60

            start_time = now - seconds_back

            self.logger.debug(
                "Fetching %s bars for %s from %d to %d (timeframe: %d min)",
                count,
                symbol,
                int(start_time),
                int(now),
                timeframe_minutes,
            )

            # Use copy_rates_range with the ORIGINAL timeframe parameter (constant or numeric)
            # MT5 accepts: mt5.TIMEFRAME_M15 (15), mt5.TIMEFRAME_H1 (16385), mt5.TIMEFRAME_H4 (16388)
            # NOT numeric 60/240 - those fail with "Invalid params"
            rates = mt5.copy_rates_range(symbol, timeframe, int(start_time), int(now))

            if rates is None or len(rates) == 0:
                self.logger.error(
                    "Failed to fetch market data for %s: %s. Check if the symbol is available and has historical data.",
                    symbol,
                    mt5.last_error(),
                )
                return None
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            self.logger.debug("Fetched %d rows of market data for %s", len(df), symbol)
            return df
        except (RuntimeError, OSError, ValueError, SystemError, TypeError) as e:
            self.logger.error("Error fetching market data for %s: %s", symbol, e)
            return None

    def get_open_positions_count(self):
        """Get the number of open positions.

        Returns:
            Integer count of open positions, or 0 on error.
        """
        try:
            positions = mt5.positions_get()
            if positions is None:
                self.logger.error("Failed to get open positions: %s", mt5.last_error())
                return 0
            return len(positions)
        except (RuntimeError, OSError, ValueError) as e:
            self.logger.error("Error getting open positions count: %s", e)
            return 0

    def _validate_volume(self, symbol, volume, symbol_info):
        """Validate and adjust volume to meet symbol requirements.

        Args:
            symbol: Trading symbol.
            volume: Requested volume.
            symbol_info: MT5 symbol info object.

        Returns:
            Validated volume adjusted to meet constraints.
        """
        min_volume = getattr(symbol_info, "volume_min", 0.01)
        max_volume = getattr(symbol_info, "volume_max", 1000.0)
        volume_step = getattr(symbol_info, "volume_step", 0.01)

        if volume < min_volume:
            self.logger.warning(
                "Volume %f for %s below minimum %f, adjusting",
                volume,
                symbol,
                min_volume,
            )
            volume = min_volume

        if volume > max_volume:
            self.logger.warning(
                "Volume %f for %s exceeds maximum %f, adjusting",
                volume,
                symbol,
                max_volume,
            )
            volume = max_volume

        volume = round(volume / volume_step) * volume_step
        self.logger.debug(
            "Validated volume for %s: %f (min=%f, max=%f, step=%f)",
            symbol,
            volume,
            min_volume,
            max_volume,
            volume_step,
        )
        return volume

    def _build_order_request(
        self, action, symbol, volume, order_type, price, sl, tp, comment
    ):
        """Build MT5 order request dictionary.

        Args:
            action: MT5 trade action constant
            symbol: Trading symbol
            volume: Order volume
            order_type: MT5 order type constant
            price: Order price
            sl: Stop loss price
            tp: Take profit price
            comment: Order comment

        Returns:
            Dictionary with order parameters for mt5.order_send()
        """
        return {
            "action": action,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "type_time": mt5.ORDER_TIME_GTC,
            "comment": comment,
        }

    @mt5_safe(max_retries=5, retry_delay=2.0)
    def place_order(self, signal, strategy_name):
        """Place a trade order based on signal.

        Args:
            signal: Signal dictionary with 'symbol', 'action' (buy/sell),
                and optional 'confidence' for position sizing.
            strategy_name: Name of the strategy generating the signal.

        Returns:
            True if order placed successfully, False otherwise.
        """
        symbol = signal["symbol"]

        config = ConfigManager.get_config()
        risk_params = config.get("risk_management", {})
        stop_loss_percent = risk_params.get("stop_loss_percent", 1.0) / 100
        take_profit_percent = risk_params.get("take_profit_percent", 2.0) / 100

        action = mt5.TRADE_ACTION_DEAL
        order_type = (
            mt5.ORDER_TYPE_BUY if signal["action"] == "buy" else mt5.ORDER_TYPE_SELL
        )
        volume = signal.get("volume", 0.01)

        try:
            # Get symbol info and validate volume
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                self.logger.error(
                    "Failed to get symbol info for %s: %s", symbol, mt5.last_error()
                )
                return False

            volume = self._validate_volume(symbol, volume, symbol_info)

            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                self.logger.error(
                    "Failed to get tick data for %s: %s", symbol, mt5.last_error()
                )
                return False

            price = tick.ask if signal["action"] == "buy" else tick.bid
            sl = (
                price * (1 - stop_loss_percent)
                if signal["action"] == "buy"
                else price * (1 + stop_loss_percent)
            )
            tp = (
                price * (1 + take_profit_percent)
                if signal["action"] == "buy"
                else price * (1 - take_profit_percent)
            )

            request = self._build_order_request(
                action,
                symbol,
                volume,
                order_type,
                price,
                sl,
                tp,
                f"{strategy_name} Entry",
            )

            self.logger.debug(
                "Placing order for %s: volume=%f, type=%s, price=%f, sl=%f, tp=%f",
                symbol,
                volume,
                "BUY" if signal["action"] == "buy" else "SELL",
                price,
                sl,
                tp,
            )
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(
                    "Order failed for %s: %s (retcode: %s)",
                    symbol,
                    result.comment,
                    result.retcode,
                )
                return False

            self.logger.info(
                "Order placed successfully for %s: Order ID %s, Deal ID %s",
                symbol,
                result.order,
                result.deal,
            )
            # Trade is logged in main.py loop to avoid schema conflicts
            return True
        except (RuntimeError, OSError, ValueError, AttributeError, TypeError) as e:
            self.logger.error("Error placing order for %s: %s", symbol, e)
            return False

    @mt5_safe(max_retries=3, retry_delay=1.5)
    def monitor_and_close_positions(self, strategy_name):
        """Monitor open positions and close based on exit strategy.

        Checks all open positions against take-profit thresholds
        and closes positions that meet exit criteria.

        Args:
            strategy_name: Name of the strategy for logging.
        """
        try:
            positions = mt5.positions_get()
            if not positions:
                self.logger.debug("No open positions to monitor")
                return

            config = ConfigManager.get_config()
            risk_params = config.get("risk_management", {})
            take_profit_percent = risk_params.get("take_profit_percent", 2.0) / 100

            for pos in positions:
                symbol = pos.symbol
                position_id = pos.ticket
                entry_price = pos.price_open
                current_price = (
                    mt5.symbol_info_tick(symbol).bid
                    if pos.type == mt5.ORDER_TYPE_BUY
                    else mt5.symbol_info_tick(symbol).ask
                )
                if current_price is None:
                    self.logger.error(
                        "Failed to get current price for %s: %s",
                        symbol,
                        mt5.last_error(),
                    )
                    continue

                profit_percent = (
                    ((current_price - entry_price) / entry_price * 100)
                    if pos.type == mt5.ORDER_TYPE_BUY
                    else ((entry_price - current_price) / entry_price * 100)
                )
                if profit_percent >= take_profit_percent * 100:
                    self.close_position(
                        position_id, symbol, pos.type, pos.volume, "Profit Target"
                    )
                    continue

                if strategy_name:
                    strategy_config = next(
                        (
                            s
                            for s in config["strategies"]
                            if s["name"].lower() == strategy_name.lower()
                        ),
                        None,
                    )
                    if strategy_config:
                        strategy = StrategyFactory.create_strategy(
                            strategy_name, strategy_config["params"], self.db
                        )
                        exit_signal = strategy.generate_exit_signal(pos)
                        if exit_signal:
                            self.close_position(
                                position_id,
                                symbol,
                                pos.type,
                                pos.volume,
                                f"{strategy_name} Exit Signal",
                            )
        except (RuntimeError, OSError, ValueError) as e:
            self.logger.error("Error monitoring positions: %s", e)

    @mt5_safe(max_retries=4, retry_delay=1.0)
    def close_position(self, position_id, symbol, position_type, volume, comment):
        """Close an open position.

        Args:
            position_id: MT5 position ticket ID.
            symbol: Trading symbol.
            position_type: MT5 order type (BUY or SELL).
            volume: Position volume to close.
            comment: Closing reason comment.

        Returns:
            True if position closed successfully, False otherwise.
        """
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                self.logger.error(
                    "Failed to get tick data for %s: %s", symbol, mt5.last_error()
                )
                return False

            price = tick.bid if position_type == mt5.ORDER_TYPE_BUY else tick.ask
            close_type = (
                mt5.ORDER_TYPE_SELL
                if position_type == mt5.ORDER_TYPE_BUY
                else mt5.ORDER_TYPE_BUY
            )

            request = self._build_order_request(
                mt5.TRADE_ACTION_DEAL,
                symbol,
                volume,
                close_type,
                price,
                0.0,
                0.0,
                comment,
            )
            request["position"] = position_id

            self.logger.debug("Closing position: %s", request)
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(
                    "Failed to close position %s for %s: %s, retcode: %s",
                    position_id,
                    symbol,
                    result.comment,
                    result.retcode,
                )
                return False

            self.logger.info(
                "Position %s closed successfully for %s: Order ID %s, Deal ID %s",
                position_id,
                symbol,
                result.order,
                result.deal,
            )
            try:
                self.db.execute_query(
                    "UPDATE trades SET exit_price = ?, exit_timestamp = ? WHERE order_id = ?",
                    (price, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), position_id),
                )
                self.logger.debug(
                    "Updated trade in database for Position ID %s", position_id
                )
            except (KeyError, ValueError, TypeError) as e:
                self.logger.error("Failed to update trade in database: %s", e)
            return True
        except (RuntimeError, OSError, ValueError) as e:
            self.logger.error(
                "Error closing position %s for %s: %s", position_id, symbol, e
            )
            return False

    @mt5_safe(max_retries=3, retry_delay=1.0)
    def get_account_status(self) -> dict:
        """Get current account information.
        
        Centralized method for retrieving account status to eliminate
        duplicate calls throughout the codebase.
        
        Returns:
            Dictionary with account information:
            - balance: Current account balance
            - equity: Current equity
            - margin: Used margin
            - free_margin: Free margin available
            - margin_level: Margin level percentage
            - profit: Current floating profit/loss
            
            Returns empty dict if account info unavailable.
            
        Example:
            >>> account = mt5_conn.get_account_status()
            >>> print(f"Balance: {account['balance']}")
        """
        try:
            account = mt5.account_info()
            if account is None:
                self.logger.warning("Failed to get account info: %s", mt5.last_error())
                return {}
            
            return {
                "balance": account.balance,
                "equity": account.equity,
                "margin": account.margin,
                "free_margin": account.margin_free,
                "margin_level": account.margin_level,
                "profit": account.profit,
                "currency": account.currency,
                "leverage": account.leverage,
                "name": account.name,
                "server": account.server,
                "login": account.login,
            }
            
        except (RuntimeError, AttributeError) as e:
            self.logger.error("Error getting account status: %s", e)
            return {}

    @mt5_safe(max_retries=3, retry_delay=1.0)
    def get_open_positions(self, symbol: str = None) -> list:
        """Get currently open positions.
        
        Centralized method for retrieving open positions to eliminate
        duplicate mt5.positions_get() calls throughout the codebase.
        
        Args:
            symbol: Optional symbol filter. If provided, returns only positions
                   for that symbol. If None, returns all open positions.
        
        Returns:
            List of position objects. Empty list if no positions or error.
            
        Example:
            >>> all_positions = mt5_conn.get_open_positions()
            >>> eurusd_positions = mt5_conn.get_open_positions("EURUSD")
            >>> position_count = len(mt5_conn.get_open_positions())
        """
        try:
            if symbol:
                positions = mt5.positions_get(symbol=symbol)
            else:
                positions = mt5.positions_get()
            
            if positions is None:
                self.logger.debug("No open positions found")
                return []
            
            return list(positions)
            
        except (RuntimeError, TypeError) as e:
            self.logger.error("Error getting open positions: %s", e)
            return []
