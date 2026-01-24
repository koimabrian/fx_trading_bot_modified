"""Volatility analysis and pair ranking for the FX Trading Bot.

Provides ATR-based volatility calculation and pair ranking to prioritize
high-volatility pairs for live trading. Implements the volatility filtering
strategy from the hybrid workflow.
"""

import logging
from typing import List, Dict, Tuple, Optional

import pandas as pd
import ta


class VolatilityManager:
    """Manages volatility calculations and pair ranking based on ATR."""

    def __init__(self, config: Dict, db):
        """Initialize VolatilityManager.

        Args:
            config: Configuration dictionary with volatility settings
            db: Database manager instance
        """
        self.config = config
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.volatility_config = config.get("volatility", {})
        self.atr_period = self.volatility_config.get("atr_period", 14)
        self.min_threshold = self.volatility_config.get("min_threshold", 0.001)
        self.lookback_bars = self.volatility_config.get("lookback_bars", 200)
        self.top_n_pairs = self.volatility_config.get("top_n_pairs", 10)

    def calculate_atr(
        self, data: pd.DataFrame, period: Optional[int] = None
    ) -> pd.DataFrame:
        """Calculate Average True Range (ATR) for volatility measurement.

        Args:
            data: DataFrame with 'high', 'low', 'close' columns
            period: ATR period (uses config default if None)

        Returns:
            DataFrame with 'atr' column added
        """
        if data.empty or len(data) < period or period is None:
            period = self.atr_period

        if len(data) < period:
            self.logger.warning(
                "Insufficient data for ATR calculation: %d rows, need %d",
                len(data),
                period,
            )
            data["atr"] = 0
            return data

        try:
            atr_indicator = ta.volatility.AverageTrueRange(
                high=data["high"],
                low=data["low"],
                close=data["close"],
                window=period,
            )
            data["atr"] = atr_indicator.average_true_range()
            return data
        except (ValueError, KeyError, TypeError) as e:
            self.logger.error("Failed to calculate ATR: %s", e)
            data["atr"] = 0
            return data

    def get_latest_atr(self, data: pd.DataFrame) -> float:
        """Get the latest ATR value from data.

        Args:
            data: DataFrame with 'atr' column

        Returns:
            Latest ATR value (0 if unavailable)
        """
        if data.empty or "atr" not in data.columns:
            return 0.0
        return float(data["atr"].iloc[-1])

    def rank_pairs_by_volatility(
        self, pairs_data: Dict[str, pd.DataFrame], symbol_filter: Optional[str] = None
    ) -> List[Tuple[str, float, str]]:
        """Rank symbol/timeframe combinations by ATR volatility.

        Args:
            pairs_data: Dict mapping 'SYMBOL_TIMEFRAME' to DataFrame
            symbol_filter: Optional single symbol to filter by

        Returns:
            List of (symbol, atr_value, timeframe) tuples sorted by ATR descending
        """
        rankings = []

        for key, data in pairs_data.items():
            if data.empty or len(data) < self.lookback_bars:
                continue

            # Parse key as 'SYMBOL_TIMEFRAME'
            if "_" not in key:
                continue

            symbol, timeframe = key.rsplit("_", 1)

            if symbol_filter and symbol != symbol_filter:
                continue

            # Use only recent lookback_bars for ranking
            lookback_data = data.tail(self.lookback_bars).copy()
            lookback_data = self.calculate_atr(lookback_data)

            latest_atr = self.get_latest_atr(lookback_data)

            if latest_atr >= self.min_threshold:
                rankings.append((symbol, latest_atr, timeframe))
            else:
                self.logger.debug(
                    "Skipping %s (%s): ATR %.6f < threshold %.6f",
                    symbol,
                    timeframe,
                    latest_atr,
                    self.min_threshold,
                )

        # Sort by ATR descending
        rankings.sort(key=lambda x: x[1], reverse=True)

        # Log skipped pairs
        if len(rankings) > self.top_n_pairs:
            skipped = rankings[self.top_n_pairs :]
            self.logger.info(
                "Volatility ranking: %d pairs above threshold, "
                "selecting top %d, skipping %d low-vol pairs",
                len(rankings),
                self.top_n_pairs,
                len(skipped),
            )
            for symbol, atr_val, tf in skipped[:5]:  # Log first 5 skipped
                self.logger.debug("  Skipped: %s (%s) - ATR: %.6f", symbol, tf, atr_val)

        return rankings[: self.top_n_pairs]

    def fetch_live_data(
        self, symbol: str, timeframe: str
    ) -> Tuple[Optional[pd.DataFrame], float]:
        """Fetch live market data and calculate ATR for a symbol/timeframe.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe string (e.g., 'M15', 'H1')

        Returns:
            Tuple of (DataFrame, latest_atr) or (None, 0) if data unavailable
        """
        try:
            from src.core.data_fetcher import DataFetcher

            fetcher = DataFetcher(None, self.db, self.config)
            data = fetcher.fetch_data(
                symbol,
                timeframe,
                table="market_data",
                required_rows=self.lookback_bars,
            )

            if data.empty:
                return None, 0.0

            data = self.calculate_atr(data)
            latest_atr = self.get_latest_atr(data)
            return data, latest_atr

        except (OSError, ValueError, KeyError) as e:
            self.logger.error(
                "Failed to fetch live data for %s (%s): %s", symbol, timeframe, e
            )
            return None, 0.0

    def should_skip_pair(self, atr_value: float) -> bool:
        """Check if a pair should be skipped due to low volatility.

        Args:
            atr_value: Latest ATR value

        Returns:
            True if pair should be skipped, False otherwise
        """
        return atr_value < self.min_threshold
