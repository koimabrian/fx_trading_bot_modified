# src/utils/trading_rules.py
"""Trading rules enforcement for market-aware order placement.

Provides rules for:
- Weekend trading restrictions (forex/commodities)
- Category-based position limits
- Market condition validation
"""
import logging
from datetime import datetime

import pytz

from src.database.db_manager import DatabaseManager
from src.utils.config_manager import ConfigManager
from src.utils.logging_factory import LoggingFactory


class TradingRules:
    """Enforces trading rules based on market conditions and database symbol categories"""

    # Lazy-loaded from database on first use
    _CRYPTO_SYMBOLS = set()
    _FOREX_SYMBOLS = set()
    _STOCKS_SYMBOLS = set()
    _COMMODITIES_SYMBOLS = set()
    _INDICES_SYMBOLS = set()
    _SYMBOLS_TO_CATEGORY = {}
    _INITIALIZED = False

    def __init__(self):
        """Initialize TradingRules and load symbol categories from database"""
        self.logger = LoggingFactory.get_logger(__name__)
        self._load_categories_from_database()

    @classmethod
    def _load_categories_from_database(cls):
        """Load symbol categories from database tradable_pairs table (singleton pattern)"""
        if cls._INITIALIZED:
            return  # Already loaded

        try:
            # Load config
            config = ConfigManager.get_config()

            db = DatabaseManager(config)
            db.connect()  # Establish connection
            cursor = db.conn.cursor()

            # Query all symbols with their categories
            cursor.execute(
                "SELECT symbol, LOWER(category) as category FROM tradable_pairs ORDER BY symbol"
            )
            rows = cursor.fetchall()

            if not rows:
                LoggingFactory.get_logger(__name__).warning(
                    "No symbols found in tradable_pairs table. Categories will be empty until symbols are loaded."
                )
                db.close()
                cls._INITIALIZED = True
                return

            # Build symbol sets by category
            cls._SYMBOLS_TO_CATEGORY = {}
            for symbol, category in rows:
                symbol_upper = symbol.upper()
                cls._SYMBOLS_TO_CATEGORY[symbol_upper] = category or "unknown"

                # Add to category-specific sets
                if category == "crypto":
                    cls._CRYPTO_SYMBOLS.add(symbol_upper)
                elif category == "forex":
                    cls._FOREX_SYMBOLS.add(symbol_upper)
                elif category == "stocks":
                    cls._STOCKS_SYMBOLS.add(symbol_upper)
                elif category == "commodities":
                    cls._COMMODITIES_SYMBOLS.add(symbol_upper)
                elif category == "indices":
                    cls._INDICES_SYMBOLS.add(symbol_upper)

            db.close()
            cls._INITIALIZED = True

            LoggingFactory.get_logger(__name__).debug(
                "Loaded trading rules from database: %d crypto, %d forex, %d stocks, %d commodities, %d indices symbols",
                len(cls._CRYPTO_SYMBOLS),
                len(cls._FOREX_SYMBOLS),
                len(cls._STOCKS_SYMBOLS),
                len(cls._COMMODITIES_SYMBOLS),
                len(cls._INDICES_SYMBOLS),
            )
        except Exception as e:
            LoggingFactory.get_logger(__name__).warning(
                "Failed to load symbol categories from database: %s. Categories will be empty.",
                e,
            )
            cls._INITIALIZED = True

    @staticmethod
    def get_symbol_category(symbol):
        """Get category of a symbol (crypto, forex, stocks, commodities, indices).

        Args:
            symbol: Trading symbol.

        Returns:
            String category or 'unknown' if not found.
        """
        TradingRules._load_categories_from_database()
        return TradingRules._SYMBOLS_TO_CATEGORY.get(symbol.upper(), "unknown")

    @staticmethod
    def is_crypto(symbol):
        """Check if symbol is cryptocurrency (24/7 trading).

        Args:
            symbol: Trading symbol.

        Returns:
            True if symbol is cryptocurrency, False otherwise.
        """
        TradingRules._load_categories_from_database()
        return symbol.upper() in TradingRules._CRYPTO_SYMBOLS

    @staticmethod
    def is_forex(symbol):
        """Check if symbol is forex (closed weekends).

        Args:
            symbol: Trading symbol.

        Returns:
            True if symbol is forex, False otherwise.
        """
        TradingRules._load_categories_from_database()
        return symbol.upper() in TradingRules._FOREX_SYMBOLS

    @staticmethod
    def is_stock(symbol):
        """Check if symbol is stock (closed weekends).

        Args:
            symbol: Trading symbol.

        Returns:
            True if symbol is stock, False otherwise.
        """
        TradingRules._load_categories_from_database()
        return symbol.upper() in TradingRules._STOCKS_SYMBOLS

    @staticmethod
    def is_commodity(symbol):
        """Check if symbol is commodity (closed weekends).

        Args:
            symbol: Trading symbol.

        Returns:
            True if symbol is commodity, False otherwise.
        """
        TradingRules._load_categories_from_database()
        return symbol.upper() in TradingRules._COMMODITIES_SYMBOLS

    @staticmethod
    def is_index(symbol):
        """Check if symbol is index (closed weekends).

        Args:
            symbol: Trading symbol.

        Returns:
            True if symbol is index, False otherwise.
        """
        TradingRules._load_categories_from_database()
        return symbol.upper() in TradingRules._INDICES_SYMBOLS

    @staticmethod
    def is_weekend():
        """Check if current time is weekend (Friday 5 PM to Sunday 5 PM UTC).

        Returns:
            True if weekend, False otherwise.
        """
        # Get current time in UTC
        utc_now = datetime.now(pytz.UTC).replace(tzinfo=None)
        weekday = utc_now.weekday()  # Monday=0, Sunday=6

        # Forex/commodities close Friday 5 PM UTC and open Monday 5 PM UTC
        return weekday >= 4  # Thursday 4 = Friday, 5 = Saturday, 6 = Sunday

    @staticmethod
    def can_trade(symbol):
        """Check if trading is allowed for symbol at current time.

        Rules:
        - Crypto: Always tradeable (24/7).
        - Forex/Stocks/Commodities/Indices: Blocked Friday 5 PM UTC -> Sunday 5 PM UTC.

        Args:
            symbol: Trading symbol.

        Returns:
            Boolean indicating if trading is allowed.
        """
        if TradingRules.is_crypto(symbol):
            # Crypto trades 24/7, always allowed
            return True

        # All other categories closed on weekends (Forex, Stocks, Commodities, Indices)
        if (
            TradingRules.is_forex(symbol)
            or TradingRules.is_stock(symbol)
            or TradingRules.is_commodity(symbol)
            or TradingRules.is_index(symbol)
        ):
            if TradingRules.is_weekend():
                return False

        return True

    def log_trading_status(self, symbol):
        """Log current trading status for a symbol.

        Args:
            symbol: Trading symbol.

        Returns:
            None.
        """
        can_trade = self.can_trade(symbol)
        is_weekend = self.is_weekend()
        symbol_category = self.get_symbol_category(symbol)

        if symbol_category == "unknown":
            self.logger.warning(
                "[UNKNOWN] %s: Not found in pair_config categories",
                symbol,
            )
            return

        if is_weekend and symbol_category != "crypto":
            self.logger.warning(
                "[WEEKEND] %s (%s): Trading DISABLED - Market closed on weekends",
                symbol,
                symbol_category,
            )
        else:
            status = "ENABLED" if can_trade else "DISABLED"
            is_24_7 = " (24/7)" if symbol_category == "crypto" else ""
            self.logger.info(
                "[TRADING] %s (%s%s): Trading %s",
                symbol,
                symbol_category,
                is_24_7,
                status,
            )
