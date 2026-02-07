"""Abstract base class for trading strategies.

Defines the interface that all trading strategies must implement,
including signal generation, data fetching, and backtesting support.
"""

from abc import ABC, abstractmethod

from src.core.data_fetcher import DataFetcher
from src.utils.logging_factory import LoggingFactory


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies.

    Provides common validation methods and interfaces for all strategy implementations.
    """

    def __init__(self, params, db, config, mode="live"):
        """Initialize strategy with parameters, database, config, and mode.

        Args:
            params: Strategy parameters dict with symbol, timeframe, volume.
            db: Database manager instance.
            config: Configuration dictionary.
            mode: Operating mode ('live' or 'backtest').
        """
        self.default_symbol = params.get("symbol", "BTCUSD")
        self.symbol = self.default_symbol
        self.timeframe = params.get("timeframe", 15)
        self.volume = params.get("volume", 0.01)
        self.db = db
        self.config = config
        self.mode = mode
        self.logger = LoggingFactory.get_logger(__name__)
        self.data_cache = None  # Set by StrategyManager

    def validate_indicator(self, value):
        """Validate indicator value for NaN or invalid values.

        Args:
            value: Indicator value to validate (float or numpy value)

        Returns:
            bool: True if valid (not NaN), False otherwise
        """
        from src.utils.value_validator import ValueValidator

        if not ValueValidator.is_valid_number(value):
            self.logger.warning(
                "Skipping signal due to invalid indicator value: %s", value
            )
            return False
        return True

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
        # Use unified market_data table for both live and backtest
        cache_key = f"{symbol_to_fetch}_{self.timeframe}"

        # Check cache first (only in live mode)
        if self.data_cache is not None and self.mode == "live":
            cached_data = self.data_cache.get(cache_key)
            if cached_data is not None:
                return cached_data

        data_fetcher = DataFetcher(None, self.db, self.config)
        data = data_fetcher.fetch_data(
            symbol_to_fetch,
            f"M{self.timeframe}",
            required_rows=required_rows,
        )

        # Cache result (only in live mode)
        if self.data_cache is not None and self.mode == "live" and not data.empty:
            self.data_cache.set(cache_key, data)

        return data

    def validate_data(self, data, required_period: int) -> bool:
        """Validate if data has sufficient rows for indicator calculation.

        Args:
            data: DataFrame to validate
            required_period: Required minimum period (e.g., RSI period, EMA period)

        Returns:
            bool: True if data is valid, False otherwise
        """
        from src.utils.value_validator import ValueValidator
        
        return ValueValidator.has_sufficient_data(
            data, required_period + 1, context=f"Strategy {self.symbol}"
        )

    def calculate_atr(self, data, period: int = 14):
        """Calculate ATR (Average True Range) volatility indicator.

        Args:
            data: DataFrame with OHLC data
            period: ATR period (default 14)

        Returns:
            DataFrame with 'atr' and 'atr_pct' columns added
        """
        import ta

        atr = ta.volatility.AverageTrueRange(
            data["high"], data["low"], data["close"], window=period
        )
        data["atr"] = atr.average_true_range()
        data["atr_pct"] = (data["atr"] / data["close"]) * 100
        return data

    def create_base_signal(self, symbol: str = None) -> dict:
        """Create base signal dictionary structure.

        Args:
            symbol: Trading symbol (uses self.symbol if None)

        Returns:
            dict: Base signal with symbol, volume, and timeframe
        """
        return {
            "symbol": symbol or self.symbol,
            "volume": self.volume,
            "timeframe": self.timeframe,
        }

    def get_latest_data(self, data):
        """Get latest candle and previous candles for analysis.

        Args:
            data: DataFrame with market data

        Returns:
            Tuple of (latest, prev, prev2) or (None, None, None) if insufficient data
        """
        if len(data) < 2:
            return None, None, None

        latest = data.iloc[-1]
        prev = data.iloc[-2]
        prev2 = data.iloc[-3] if len(data) > 2 else None

        return latest, prev, prev2

    @abstractmethod
    def generate_entry_signal(self, symbol=None):
        """Generate an entry signal for the given symbol.

        Args:
            symbol: Trading symbol (uses default if None).

        Returns:
            Signal dict with action, symbol, volume, or None if no signal.
        """

    @abstractmethod
    def generate_exit_signal(self, position):
        """Generate an exit signal for an open position.

        Args:
            position: Position dict with symbol, entry_price, etc.

        Returns:
            Exit signal dict or None if position should be held.
        """
