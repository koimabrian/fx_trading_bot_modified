# fx_trading_bot/src/core/data_handler.py
# Purpose: Manages backtesting data preparation and storage
import logging

import pandas as pd


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
        self.logger = logging.getLogger(__name__)

    def prepare_backtest_data(self, symbol, timeframe):
        """Prepare data for backtesting from database.
        Uses all available data in backtest_market_data table (no date filtering).
        Falls back to market_data if backtest_market_data is empty.
        """
        try:
            # Fetch all available data for the symbol and timeframe (no date range filtering)
            query = """
                SELECT * FROM backtest_market_data
                WHERE symbol = ? AND timeframe = ?
                ORDER BY time ASC
            """
            data = pd.read_sql(query, self.db.conn, params=(symbol, timeframe))

            # Fallback: if backtest_market_data is empty, try market_data
            if data.empty:
                self.logger.debug(
                    "backtest_market_data empty for %s (%s), trying market_data fallback",
                    symbol,
                    timeframe,
                )
                query = """
                    SELECT * FROM market_data
                    WHERE symbol = ? AND timeframe = ?
                    ORDER BY time ASC
                """
                data = pd.read_sql(query, self.db.conn, params=(symbol, timeframe))

                if data.empty:
                    self.logger.warning(
                        "No data available for %s (%s) in either backtest_market_data or market_data.",
                        symbol,
                        timeframe,
                    )
                    self.logger.warning(
                        "To populate data: python -m src.main --mode live --strategy rsi (run for 30-60s)"
                    )
                    self.logger.warning(
                        "Then sync: python -m src.backtesting.backtest_manager --mode sync --symbol %s",
                        symbol,
                    )
                    return None
                else:
                    self.logger.info(
                        "Using market_data as fallback for %s (%s)", symbol, timeframe
                    )

            # Rename columns to match backtesting.py requirements
            data = data.rename(
                columns={
                    "time": "Datetime",
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "tick_volume": "Volume",
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
