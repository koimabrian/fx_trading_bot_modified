"""Abstract base class for trading strategies.

Defines the interface that all trading strategies must implement,
including signal generation, data fetching, and backtesting support.
"""

import logging
from abc import ABC, abstractmethod

from src.core.data_fetcher import DataFetcher


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""

    def __init__(self, params, db, config, mode="live"):
        """Initialize strategy with parameters, database, config, and mode"""
        self.default_symbol = params.get("symbol", "BTCUSD")
        self.symbol = self.default_symbol
        self.timeframe = params.get("timeframe", 15)
        self.volume = params.get("volume", 0.01)
        self.db = db
        self.config = config
        self.mode = mode
        self.logger = logging.getLogger(__name__)
        self.data_cache = None  # Set by StrategyManager

    def fetch_data(self, symbol=None, required_rows=None):
        """Fetch market data for the strategy using DataFetcher.

        Args:
            symbol: Trading symbol (uses self.symbol if None)
            required_rows: Minimum rows needed (e.g., RSI period + buffer)
                          If None, uses config fetch_limit

        Returns:
            DataFrame with market data
        """
        symbol_to_fetch = symbol or self.symbol
        table = "backtest_market_data" if self.mode == "backtest" else "market_data"
        cache_key = f"{symbol_to_fetch}_{self.timeframe}_{table}"

        # Check cache first (only in live mode)
        if self.data_cache is not None and self.mode == "live":
            cached_data = self.data_cache.get(cache_key)
            if cached_data is not None:
                return cached_data

        data_fetcher = DataFetcher(None, self.db, self.config)
        data = data_fetcher.fetch_data(
            symbol_to_fetch,
            f"M{self.timeframe}",
            table=table,
            required_rows=required_rows,
        )

        # Cache result (only in live mode)
        if self.data_cache is not None and self.mode == "live" and not data.empty:
            self.data_cache.set(cache_key, data)

        return data

    @abstractmethod
    def generate_entry_signal(self, symbol=None):
        """Generate an entry signal"""

    @abstractmethod
    def generate_exit_signal(self, position):
        """Generate an exit signal for an open position"""
