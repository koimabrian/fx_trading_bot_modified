# fx_trading_bot/src/mt5_connector.py
# Purpose: Manages connection and operations with MetaTrader 5
import MetaTrader5 as mt5
import pandas as pd
import os
import logging
import yaml
from datetime import datetime
from src.strategies.factory import StrategyFactory

class MT5Connector:
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger(__name__)
        # Load credentials from config.yaml or environment variables
        with open('src/config/config.yaml', 'r') as file:
            config = yaml.safe_load(file)
        mt5_config = config.get('mt5', {})
        self.login = int(os.getenv("MT5_LOGIN", mt5_config.get('login', 0)))
        self.password = os.getenv("MT5_PASSWORD", mt5_config.get('password', ""))
        self.server = os.getenv("MT5_SERVER", mt5_config.get('server', ""))

    def initialize(self):
        """Initialize MT5 connection with config"""
        if not self.login or not self.password or not self.server:
            self.logger.error("MT5 credentials missing. Please update src/config/config.yaml or set MT5_LOGIN, MT5_PASSWORD, MT5_SERVER environment variables.")
            return False

        try:
            self.logger.debug(f"Attempting MT5 connection with login={self.login}, server={self.server}")
            if not mt5.initialize(login=self.login, password=self.password, server=self.server, timeout=30000):
                error_code, error_msg = mt5.last_error()
                self.logger.error(f"MT5 initialization failed: Error code {error_code}, Message: {error_msg}")
                self.logger.info("Possible causes: MT5 terminal not running, invalid credentials, incorrect server name, or network issues.")
                self.logger.info("Ensure MetaTrader 5 is running, credentials are correct, and the server (e.g., Exness-MT5Trial9) is accessible.")
                return False
            self.logger.info("MT5 connection initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Unexpected error during MT5 initialization: {e}")
            return False

    def fetch_market_data(self, symbol, timeframe, count=1000):
        """Fetch market data from MT5 with improved error handling and logging."""
        try:
            if not mt5.symbol_select(symbol, True):
                self.logger.error(f"Failed to select {symbol} in Market Watch: {mt5.last_error()}. Make sure the symbol is available in your MT5 terminal.")
                return None

            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
            if rates is None or len(rates) == 0:
                self.logger.error(f"Failed to fetch market data for {symbol}: {mt5.last_error()}. Check if the symbol is available and has historical data.")
                return None
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            self.logger.debug(f"Fetched {len(df)} rows of market data for {symbol}")
            return df
        except Exception as e:
            self.logger.error(f"Error fetching market data for {symbol}: {e}")
            return None

    def get_open_positions_count(self):
        """Get the number of open positions"""
        try:
            positions = mt5.positions_get()
            if positions is None:
                self.logger.error(f"Failed to get open positions: {mt5.last_error()}")
                return 0
            return len(positions)
        except Exception as e:
            self.logger.error(f"Error getting open positions count: {e}")
            return 0

    def place_order(self, signal, strategy_name):
        """Implement trade order placement logic"""
        with open('src/config/config.yaml', 'r') as file:
            config = yaml.safe_load(file)
        risk_params = config.get('risk_management', {})
        stop_loss_percent = risk_params.get('stop_loss_percent', 1.0) / 100
        take_profit_percent = risk_params.get('take_profit_percent', 2.0) / 100

        symbol = signal['symbol']
        action = mt5.TRADE_ACTION_DEAL
        order_type = mt5.ORDER_TYPE_BUY if signal['action'] == 'buy' else mt5.ORDER_TYPE_SELL
        volume = signal.get('volume', 0.01)

        try:
            if not mt5.symbol_select(symbol, True):
                self.logger.error(f"Failed to select {symbol} in Market Watch: {mt5.last_error()}")
                return False

            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                self.logger.error(f"Failed to get tick data for {symbol}: {mt5.last_error()}")
                return False

            price = tick.ask if signal['action'] == 'buy' else tick.bid
            sl = price * (1 - stop_loss_percent) if signal['action'] == 'buy' else price * (1 + stop_loss_percent)
            tp = price * (1 + take_profit_percent) if signal['action'] == 'buy' else price * (1 - take_profit_percent)
            request = {
                "action": action,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "price": price,
                "sl": sl,
                "tp": tp,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
                "comment": f"{strategy_name} Entry"
            }

            self.logger.debug(f"Placing order: {request}")
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Order failed for {symbol}: {result.comment}, retcode: {result.retcode}")
                return False

            self.logger.info(f"Order placed successfully for {symbol}: Order ID {result.order}, Deal ID {result.deal}")
            try:
                strategy_id = self.db.execute_query(
                    "SELECT id FROM strategies WHERE name = ? LIMIT 1",
                    (strategy_name.lower(),)
                )[0]['id']
                self.db.execute_query(
                    "INSERT INTO trades (strategy_id, pair, entry_price, volume, timestamp, mode, order_id, deal_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (strategy_id, symbol, price, volume, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'live', result.order, result.deal)
                )
                self.logger.debug(f"Logged trade to database: Strategy {strategy_name}, Symbol {symbol}, Order ID {result.order}")
            except Exception as e:
                self.logger.error(f"Failed to log trade to database: {e}")
            return True
        except Exception as e:
            self.logger.error(f"Error placing order for {symbol}: {e}")
            return False

    def monitor_and_close_positions(self, strategy_name):
        """Monitor open positions and close based on exit strategy or profitability"""
        try:
            positions = mt5.positions_get()
            if not positions:
                self.logger.debug("No open positions to monitor")
                return

            with open('src/config/config.yaml', 'r') as file:
                config = yaml.safe_load(file)
            risk_params = config.get('risk_management', {})
            take_profit_percent = risk_params.get('take_profit_percent', 2.0) / 100

            for pos in positions:
                symbol = pos.symbol
                position_id = pos.ticket
                entry_price = pos.price_open
                current_price = mt5.symbol_info_tick(symbol).bid if pos.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).ask
                if current_price is None:
                    self.logger.error(f"Failed to get current price for {symbol}: {mt5.last_error()}")
                    continue

                profit_percent = ((current_price - entry_price) / entry_price * 100) if pos.type == mt5.ORDER_TYPE_BUY else ((entry_price - current_price) / entry_price * 100)
                if profit_percent >= take_profit_percent * 100:
                    self.close_position(position_id, symbol, pos.type, pos.volume, "Profit Target")
                    continue

                if strategy_name:
                    strategy_config = next((s for s in config['strategies'] if s['name'].lower() == strategy_name.lower()), None)
                    if strategy_config:
                        strategy = StrategyFactory.create_strategy(strategy_name, strategy_config['params'], self.db)
                        exit_signal = strategy.generate_exit_signal(pos)
                        if exit_signal:
                            self.close_position(position_id, symbol, pos.type, pos.volume, f"{strategy_name} Exit Signal")
        except Exception as e:
            self.logger.error(f"Error monitoring positions: {e}")

    def close_position(self, position_id, symbol, position_type, volume, comment):
        """Close an open position"""
        try:
            if not mt5.symbol_select(symbol, True):
                self.logger.error(f"Failed to select {symbol} in Market Watch: {mt5.last_error()}")
                return False

            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                self.logger.error(f"Failed to get tick data for {symbol}: {mt5.last_error()}")
                return False

            price = tick.bid if position_type == mt5.ORDER_TYPE_BUY else tick.ask
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_SELL if position_type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
                "position": position_id,
                "price": price,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
                "comment": comment
            }

            self.logger.debug(f"Closing position: {request}")
            result = mt5.order_send(request)
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.logger.error(f"Failed to close position {position_id} for {symbol}: {result.comment}, retcode: {result.retcode}")
                return False

            self.logger.info(f"Position {position_id} closed successfully for {symbol}: Order ID {result.order}, Deal ID {result.deal}")
            try:
                self.db.execute_query(
                    "UPDATE trades SET exit_price = ?, exit_timestamp = ?, profit = ? WHERE order_id = ?",
                    (price, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), (price - entry_price) if position_type == mt5.ORDER_TYPE_BUY else (entry_price - price), position_id)
                )
                self.logger.debug(f"Updated trade in database for Position ID {position_id}")
            except Exception as e:
                self.logger.error(f"Failed to update trade in database: {e}")
            return True
        except Exception as e:
            self.logger.error(f"Error closing position {position_id} for {symbol}: {e}")
            return False