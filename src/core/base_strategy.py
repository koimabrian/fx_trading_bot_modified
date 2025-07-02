# src/core/base_strategy.py
from abc import ABC, abstractmethod
import pandas as pd
import logging
import yaml

class BaseStrategy(ABC):
    """Abstract base class for trading strategies."""
    def __init__(self, params, db, config, mode='live'):
        """Initialize strategy with parameters, database, and config."""
        with open('src/config/config.yaml', 'r') as file:
            cfg = yaml.safe_load(file)
        self.default_symbol = cfg.get('mt5', {}).get('default_symbol', 'XAUUSD')
        self.default_volume = cfg.get('mt5', {}).get('default_volume', 0.01)
        self.mode = mode
        self.table = 'market_data' if mode == 'live' else 'backtest_market_data'
        self.symbol = params.get('symbol', self.default_symbol)
        self.timeframe = params.get('timeframe', 15)
        self.volume = params.get('volume', self.default_volume)
        self.db = db
        self.config = config
        self.logger = logging.getLogger(__name__)

    def fetch_data(self, symbol=None):
        """Fetch market data for the strategy."""
        symbol_to_fetch = symbol if symbol is not None else self.symbol
        try:
            timeframe_str = f"M{self.timeframe}" if self.timeframe < 60 else f"H{self.timeframe//60}" if self.timeframe < 1440 else 'D1'
            query = f"SELECT * FROM {self.table} WHERE symbol='{symbol_to_fetch}' AND timeframe='{timeframe_str}' ORDER BY time DESC LIMIT 100"
            data = pd.read_sql(query, self.db.conn)
            self.logger.debug(f"Fetched {len(data)} rows from database for {symbol_to_fetch}")
            return data
        except Exception as e:
            self.logger.error(f"Failed to fetch data from database: {e}")
            return pd.DataFrame()

    @abstractmethod
    def generate_entry_signal(self, symbol=None):
        """Generate an entry signal."""
        pass

    @abstractmethod
    def generate_exit_signal(self, position):
        """Generate an exit signal for an open position."""
        pass