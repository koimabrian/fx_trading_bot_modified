"""Strategy management with caching and signal generation.

Manages dynamic loading of trading strategies with performance
optimization via TTL-based data caching. Supports both live and
backtest modes with automatic signal generation across multiple
timeframes and symbols.
"""

import time
from typing import Any, Dict, List, Optional

import pandas as pd

from src.strategies.factory import StrategyFactory
from src.utils.logging_factory import LoggingFactory


class DataCache:
    """In-memory cache for market data with time-to-live (TTL) support."""

    def __init__(self, ttl_seconds: int = 20):
        """Initialize cache with TTL.

        Args:
            ttl_seconds: Cache expiration time in seconds (default 20s for live mode)
        """
        self.cache: Dict[str, pd.DataFrame] = {}
        self.timestamps: Dict[str, float] = {}
        self.ttl = ttl_seconds
        self.logger = LoggingFactory.get_logger(__name__)

    def get(self, key: str) -> Optional[pd.DataFrame]:
        """Retrieve cached data if still valid.

        Args:
            key: Cache key (e.g., 'BTCUSD_15_market_data')

        Returns:
            DataFrame if found and not expired, None otherwise
        """
        if key in self.cache:
            age = time.time() - self.timestamps[key]
            if age < self.ttl:
                self.logger.debug("Cache HIT: %s (age: %.1fs)", key, age)
                return self.cache[key]
            # Expired entry
            del self.cache[key]
            del self.timestamps[key]
        self.logger.debug("Cache MISS: %s", key)
        return None

    def set(self, key: str, value: pd.DataFrame) -> None:
        """Store data in cache.

        Args:
            key: Cache key
            value: DataFrame to cache
        """
        self.cache[key] = value
        self.timestamps[key] = time.time()
        self.logger.debug("Cache SET: %s", key)

    def clear(self) -> None:
        """Clear entire cache."""
        self.cache.clear()
        self.timestamps.clear()
        self.logger.debug("Cache cleared")

    def get_size(self) -> int:
        """Get number of cached items.

        Returns:
            Number of items currently in cache.
        """
        return len(self.cache)


class StrategyManager:
    """Manages dynamic loading and execution of rule-based trading strategies."""

    def __init__(self, db, mode="live", symbol=None):
        """Initialize strategy manager with config and database.

        Args:
            db: Database manager instance
            mode: Trading mode ('live' or 'backtest')
            symbol: Optional specific trading symbol to focus on
        """
        self.db = db
        self.mode = mode
        self.symbol = symbol  # Store symbol filter if provided
        self.strategies = []
        self.data_cache = DataCache(ttl_seconds=20)
        self.logger = LoggingFactory.get_logger(__name__)
        self.config = {}  # Store config for use in generate_signals
        self.load_config()

    def load_config(self) -> None:
        """Load and instantiate strategies from YAML configuration.

        Reads strategy configurations from config.yaml via ConfigManager,
        creates strategy instances using StrategyFactory, and attaches
        the shared data cache to each strategy.

        Raises:
            Exception: If configuration file cannot be loaded.
        """
        try:
            from src.utils.config_manager import ConfigManager

            config = ConfigManager.get_config()
            self.config = config  # Store config for generate_signals
            for strategy_config in config.get("strategies", []):
                strategy_name = strategy_config["name"]
                params = strategy_config["params"]
                try:
                    strategy = StrategyFactory.create_strategy(
                        strategy_name, params, self.db, self.mode
                    )
                    strategy.data_cache = self.data_cache
                    self.strategies.append(strategy)
                except (ImportError, KeyError, ValueError, TypeError) as e:
                    self.logger.error(
                        "Failed to load strategy %s: %s", strategy_name, e
                    )
            self.logger.debug("Loaded %d strategies", len(self.strategies))
        except Exception as e:
            self.logger.error("Failed to load strategy config: %s", e)
            raise

    def generate_signals(
        self, strategy_name: Optional[str] = None, symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate entry signals for tradable pairs using loaded strategies.

        Queries tradable_pairs from the database and generates entry signals
        for each symbol/strategy combination. Symbol filtering priority:
        method argument > instance symbol > all database symbols.

        Args:
            strategy_name: Optional filter to run only strategies matching
                this name prefix (case-insensitive).
            symbol: Optional specific symbol to generate signals for.

        Returns:
            List of signal dictionaries from strategies that generated
            entry signals. Empty list if no signals or on error.
        """
        try:
            signals = []

            # Get all unique symbols from database
            if not hasattr(self, "db") or not self.db:
                self.logger.debug("Database not available for signal generation")
                return []

            cursor = self.db.conn.cursor()
            cursor.execute("SELECT DISTINCT symbol FROM tradable_pairs ORDER BY symbol")
            config_symbols = [row[0] for row in cursor.fetchall()]

            if not config_symbols:
                self.logger.debug("No symbols found in database")
                return []  # Return empty list if no symbols in database

            # Determine which symbol(s) to process
            # Priority: method arg > instance symbol > all config symbols
            if symbol:
                symbols_to_process = [symbol]
            elif self.symbol:
                symbols_to_process = [self.symbol]
            else:
                symbols_to_process = config_symbols

            for pair_symbol in symbols_to_process:
                for strategy in self.strategies:
                    # Filter by strategy name if specified
                    if (
                        strategy_name
                        and not strategy.__class__.__name__.lower().startswith(
                            strategy_name.lower()
                        )
                    ):
                        continue

                    # Generate signal for this symbol/strategy combination
                    signal = strategy.generate_entry_signal(symbol=pair_symbol)
                    if signal:
                        signals.append(signal)
                        self.logger.debug(
                            "Generated signal from %s for %s: %s",
                            strategy.__class__.__name__,
                            pair_symbol,
                            signal,
                        )

            return signals
        except (KeyError, ValueError, TypeError, AttributeError) as e:
            self.logger.error("Error generating signals: %s", e)
            return []  # Always return list on error
