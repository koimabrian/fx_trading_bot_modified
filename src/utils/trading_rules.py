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
import yaml


class TradingRules:
    """Enforces trading rules based on market conditions and config.yaml pair categories"""

    # Lazy-loaded from config.yaml on first use
    _CRYPTO_SYMBOLS = set()
    _FOREX_SYMBOLS = set()
    _STOCKS_SYMBOLS = set()
    _COMMODITIES_SYMBOLS = set()
    _INDICES_SYMBOLS = set()
    _SYMBOLS_TO_CATEGORY = {}
    _INITIALIZED = False

    def __init__(self):
        """Initialize TradingRules and load symbol categories from config.yaml"""
        self.logger = logging.getLogger(__name__)
        self._load_categories_from_config()

    @classmethod
    def _load_categories_from_config(cls):
        """Load symbol categories from config.yaml (singleton pattern)"""
        if cls._INITIALIZED:
            return  # Already loaded

        try:
            with open("src/config/config.yaml", "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            pair_config = config.get("pair_config", {}) or {}
            categories = pair_config.get("categories", {}) or {}

            # Initialize sets from config - handle None gracefully
            cls._CRYPTO_SYMBOLS = set(
                categories.get("crypto", {}).get("symbols", []) or []
            )
            cls._FOREX_SYMBOLS = set(
                categories.get("forex", {}).get("symbols", []) or []
            )
            cls._STOCKS_SYMBOLS = set(
                categories.get("stocks", {}).get("symbols", []) or []
            )
            cls._COMMODITIES_SYMBOLS = set(
                categories.get("commodities", {}).get("symbols", []) or []
            )
            cls._INDICES_SYMBOLS = set(
                categories.get("indices", {}).get("symbols", []) or []
            )

            # Build symbol-to-category mapping for quick lookup
            cls._SYMBOLS_TO_CATEGORY = {}
            for symbol in cls._CRYPTO_SYMBOLS:
                cls._SYMBOLS_TO_CATEGORY[symbol] = "crypto"
            for symbol in cls._FOREX_SYMBOLS:
                cls._SYMBOLS_TO_CATEGORY[symbol] = "forex"
            for symbol in cls._STOCKS_SYMBOLS:
                cls._SYMBOLS_TO_CATEGORY[symbol] = "stocks"
            for symbol in cls._COMMODITIES_SYMBOLS:
                cls._SYMBOLS_TO_CATEGORY[symbol] = "commodities"
            for symbol in cls._INDICES_SYMBOLS:
                cls._SYMBOLS_TO_CATEGORY[symbol] = "indices"

            cls._INITIALIZED = True

            logging.getLogger(__name__).debug(
                "Loaded trading rules from config: %d crypto, %d forex, %d stocks, %d commodities, %d indices symbols",
                len(cls._CRYPTO_SYMBOLS),
                len(cls._FOREX_SYMBOLS),
                len(cls._STOCKS_SYMBOLS),
                len(cls._COMMODITIES_SYMBOLS),
                len(cls._INDICES_SYMBOLS),
            )
        except (FileNotFoundError, KeyError, yaml.YAMLError) as e:
            logging.getLogger(__name__).warning(
                "Failed to load pair_config from config.yaml: %s. Pair categories will be empty until configured via init mode.",
                e,
            )
            # Initialize empty sets - user must configure pairs via init mode GUI
            cls._INITIALIZED = True

    @staticmethod
    def get_symbol_category(symbol):
        """Get category of a symbol (crypto, forex, stocks, commodities, indices)

        Returns:
            String category or 'unknown' if not found
        """
        TradingRules._load_categories_from_config()
        return TradingRules._SYMBOLS_TO_CATEGORY.get(symbol.upper(), "unknown")

    @staticmethod
    def is_crypto(symbol):
        """Check if symbol is cryptocurrency (24/7 trading)"""
        TradingRules._load_categories_from_config()
        return symbol.upper() in TradingRules._CRYPTO_SYMBOLS

    @staticmethod
    def is_forex(symbol):
        """Check if symbol is forex (closed weekends)"""
        TradingRules._load_categories_from_config()
        return symbol.upper() in TradingRules._FOREX_SYMBOLS

    @staticmethod
    def is_stock(symbol):
        """Check if symbol is stock (closed weekends)"""
        TradingRules._load_categories_from_config()
        return symbol.upper() in TradingRules._STOCKS_SYMBOLS

    @staticmethod
    def is_commodity(symbol):
        """Check if symbol is commodity (closed weekends)"""
        TradingRules._load_categories_from_config()
        return symbol.upper() in TradingRules._COMMODITIES_SYMBOLS

    @staticmethod
    def is_index(symbol):
        """Check if symbol is index (closed weekends)"""
        TradingRules._load_categories_from_config()
        return symbol.upper() in TradingRules._INDICES_SYMBOLS

    @staticmethod
    def is_weekend():
        """Check if current time is weekend (Friday 5 PM to Sunday 5 PM UTC)"""
        # Get current time in UTC
        utc_now = datetime.now(pytz.UTC).replace(tzinfo=None)
        weekday = utc_now.weekday()  # Monday=0, Sunday=6

        # Forex/commodities close Friday 5 PM UTC and open Monday 5 PM UTC
        return weekday >= 4  # Thursday 4 = Friday, 5 = Saturday, 6 = Sunday

    @staticmethod
    def can_trade(symbol):
        """Check if trading is allowed for symbol at current time

        Rules:
        - Crypto: Always tradeable (24/7)
        - Forex/Stocks/Commodities/Indices: Blocked Friday 5 PM UTC → Sunday 5 PM UTC

        Returns:
            Boolean indicating if trading is allowed
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
        """Log current trading status for a symbol"""
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
