# fx_trading_bot/src/core/base_strategy.py
# Purpose: Abstract base class for trading strategies
from abc import ABC, abstractmethod
import pandas as pd
import logging
from src.core.data_fetcher import DataFetcher

class BaseStrategy(ABC):
    def __init__(self, params, db, config, mode='live'):
        """Initialize strategy with parameters, database, config, and mode"""
        self.default_symbol = params.get('symbol', 'BTCUSDm')
        self.symbol = self.default_symbol
        self.timeframe = params.get('timeframe', 15)
        self.volume = params.get('volume', 0.01)
        self.db = db
        self.config = config
        self.mode = mode
        self.logger = logging.getLogger(__name__)

    def fetch_data(self, symbol=None):
        """Fetch market data for the strategy using DataFetcher"""
        symbol_to_fetch = symbol or self.symbol
        table = 'backtest_market_data' if self.mode == 'backtest' else 'market_data'
        data_fetcher = DataFetcher(None, self.db, self.config)
        return data_fetcher.fetch_data(symbol_to_fetch, f"M{self.timeframe}", table=table)

    @abstractmethod
    def generate_entry_signal(self, symbol=None):
        """Generate an entry signal"""
        pass

    @abstractmethod
    def generate_exit_signal(self, position):
        """Generate an exit signal for an open position"""
        pass