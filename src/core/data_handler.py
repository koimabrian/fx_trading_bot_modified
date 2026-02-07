# fx_trading_bot/src/core/data_handler.py
# Purpose: Manages backtesting data preparation and storage

import pandas as pd

from src.utils.logging_factory import LoggingFactory


class DataHandler:
    """Manages backtesting data preparation and storage."""

    def __init__(self, db, config):
        """Initialize DataHandler.

        Args:
            db: Database manager instance
            config: Configuration dictionary
        """
        self.db = db
        self.config = config
        self.logger = LoggingFactory.get_logger(__name__)

    def prepare_backtest_data(self, symbol, timeframe):
        """Prepare data for backtesting from database.
        Uses all available data in market_data table (no date filtering).

        Args:
            symbol: Currency pair symbol (e.g., 'EURUSD')
            timeframe: Timeframe string (e.g., 'H1', 'M15')

        Returns:
            DataFrame with OHLC data indexed by datetime, or None if no data available
        """
        try:
            # Fetch all available data from market_data table
            # Uses new schema: direct symbol column, tick_volume (not volume), composite key
            query = """
                SELECT open, high, low, close, tick_volume AS volume, time
                FROM market_data
                WHERE symbol = ? AND timeframe = ?
                ORDER BY time ASC
            """
            data = pd.read_sql(query, self.db.conn, params=(symbol, timeframe))

            if data.empty:
                self.logger.warning(
                    "No data available for %s (%s) in market_data.",
                    symbol,
                    timeframe,
                )
                self.logger.warning("To populate data: python -m src.main --mode sync")
                return None

            self.logger.info("Using market_data for %s (%s)", symbol, timeframe)

            # Rename columns to match backtesting.py requirements
            data = data.rename(
                columns={
                    "time": "Datetime",
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume",
                }
            )
            data["Datetime"] = pd.to_datetime(data["Datetime"])
            data.set_index("Datetime", inplace=True)
            self.logger.info(
                "Prepared %s rows for backtesting: %s (%s) [Range: %s to %s]",
                len(data),
                symbol,
                timeframe,
                data.index[0],
                data.index[-1],
            )
            return data
        except (pd.errors.DatabaseError, ValueError) as e:
            self.logger.error(
                "Failed to prepare backtest data for %s (%s): %s", symbol, timeframe, e
            )
            return None
