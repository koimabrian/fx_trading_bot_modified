# fx_trading_bot/src/core/base_strategy.py
# Purpose: Abstract base class for trading strategies
from abc import ABC, abstractmethod
import pandas as pd
import logging

class BaseStrategy(ABC):
    def __init__(self, params, db):
        """Initialize strategy with parameters and database connection"""
        self.default_symbol = params.get('symbol', 'BTCUSDm')  # Default symbol
        self.symbol = self.default_symbol
        self.timeframe = params.get('timeframe', 15)  # M15 by default
        self.volume = params.get('volume', 0.01)
        self.db = db
        self.logger = logging.getLogger(__name__)

    def fetch_data(self, symbol=None):
        """Fetch market data for the strategy"""
        symbol_to_fetch = symbol if symbol is not None else self.symbol
        try:
            timeframe_str = f"M{self.timeframe}"
            query = f"SELECT * FROM market_data WHERE symbol='{symbol_to_fetch}' AND timeframe='{timeframe_str}' ORDER BY time DESC LIMIT 100"
            data = pd.read_sql(query, self.db.conn)
            self.logger.debug(f"Fetched {len(data)} rows from database for {symbol_to_fetch}")
            return data
        except Exception as e:
            self.logger.error(f"Failed to fetch data from database: {e}")
            return pd.DataFrame()

    @abstractmethod
    def generate_entry_signal(self, symbol=None):
        """Generate an entry signal"""
        pass

    @abstractmethod
    def generate_exit_signal(self, position):
        """Generate an exit signal for an open position"""
        pass