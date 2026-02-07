# src/utils/data_validator.py
"""Validates and initializes database with quality data.

Provides DataValidator class for checking data freshness,
validating database schema, and syncing data from MT5.
"""
import logging
from datetime import datetime, timedelta

import MetaTrader5 as mt5
import pandas as pd

from src.core.data_fetcher import DataFetcher
from src.utils.logging_factory import LoggingFactory


class DataValidator:
    """Validates database health and initializes with quality data"""

    def __init__(self, db, config, mt5_conn=None):
        """Initialize DataValidator.

        Args:
            db: Database manager instance
            config: Configuration dictionary
            mt5_conn: MT5 connector instance (optional)
        """
        self.db = db
        self.config = config
        self.mt5_conn = mt5_conn
        self.logger = LoggingFactory.get_logger(__name__)
        self.min_rows_per_symbol = config.get("data", {}).get(
            "min_rows_threshold", 5000
        )

    def validate_and_init(self, symbol: str = None):
        """Main validation and initialization flow.

        Args:
            symbol: Optional specific symbol to validate. If None, validates all configured symbols.
        """
        self.logger.info("Starting database validation and initialization...")

        # Check if tables exist
        if not self._check_tables_exist():
            self.logger.info("Creating missing tables")
            self.db.create_tables()

        # Check data completeness
        pairs = self.config.get("pairs", [])
        # Filter pairs by symbol if specified
        pairs_to_check = (
            [p for p in pairs if p["symbol"] == symbol] if symbol else pairs
        )
        for pair in pairs_to_check:
            symbol = pair["symbol"]
            tf = pair["timeframe"]
            tf_str = f"M{tf}" if tf < 60 else f"H{tf//60}"

            row_count = self.get_row_count(symbol, tf_str, table="market_data")
            self.logger.info(
                "Data check: %s (%s) - %d rows in market_data",
                symbol,
                tf_str,
                row_count,
            )

            # If data is missing or insufficient, fetch from MT5
            if row_count < self.min_rows_per_symbol:
                if self.mt5_conn:
                    self.logger.warning(
                        "Insufficient data for %s (%s): %d rows. Fetching %d rows from MT5...",
                        symbol,
                        tf_str,
                        row_count,
                        self.min_rows_per_symbol,
                    )
                    self.sync_data(symbol, tf)
                else:
                    self.logger.warning(
                        "No MT5 connector provided. Skipping auto-fetch for %s", symbol
                    )

    def _check_tables_exist(self):
        """Check if market_data and backtest_market_data tables exist.

        Returns:
            True if tables exist, False otherwise.
        """
        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='market_data'"
            )
            exists = cursor.fetchone() is not None
            self.logger.debug("market_data table exists: %s", exists)
            return exists
        except (RuntimeError, ValueError, KeyError) as e:
            self.logger.error("Error checking tables: %s", e)
            return False

    def get_row_count(self, symbol, timeframe, table="market_data"):
        """Get row count for a symbol/timeframe in specified table.

        Args:
            symbol: Trading symbol.
            timeframe: Timeframe string (e.g., 'M15', 'H1').
            table: Table name to query (default: market_data).

        Returns:
            Integer row count for the specified symbol and timeframe.
        """
        try:
            # Query market_data using direct symbol column (new schema)
            query = f"SELECT COUNT(*) as cnt FROM {table} WHERE symbol = ? AND timeframe = ?"
            result = (
                self.db.conn.cursor().execute(query, (symbol, timeframe)).fetchone()
            )
            return result[0] if result else 0
        except (RuntimeError, ValueError, KeyError, TypeError) as e:
            self.logger.debug(
                "Error getting row count for %s (%s): %s", symbol, timeframe, e
            )
            return 0

    def sync_data(self, symbol, timeframe):
        """Fetch data from MT5 and sync to market_data table.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSD')
            timeframe: Timeframe in minutes (15, 60, 240) or None to sync all timeframes
        """
        try:
            if not self.mt5_conn.initialize():
                self.logger.error("Failed to initialize MT5 for %s", symbol)
                return

            # If timeframe is None, sync all configured timeframes for the symbol
            # Default timeframes are now in config.yaml timeframes section
            timeframes_to_sync = (
                [timeframe]
                if timeframe is not None
                else self.config.get("timeframes", [15, 60, 240])
            )

            for tf in timeframes_to_sync:
                tf_str = f"M{tf}" if tf < 60 else f"H{tf//60}"

                # Map numeric timeframe to MT5 constant correctly
                tf_map = {
                    15: mt5.TIMEFRAME_M15,
                    60: mt5.TIMEFRAME_H1,
                    240: mt5.TIMEFRAME_H4,
                }
                mt5_tf = tf_map.get(tf, mt5.TIMEFRAME_M15)

                data_fetcher = DataFetcher(self.mt5_conn, self.db, self.config)
                # Call sync_data without table parameter (uses unified market_data by default)
                data_fetcher.sync_data(symbol, mt5_timeframe=mt5_tf)

                new_count = self.get_row_count(symbol, tf_str, table="market_data")
                self.logger.info(
                    "Synced data for %s (%s): now %d rows", symbol, tf_str, new_count
                )
        except (RuntimeError, ValueError, KeyError, TypeError) as e:
            self.logger.error("Failed to fetch and sync data for %s: %s", symbol, e)

    def check_data_freshness(self, symbol, timeframe, max_age_hours=24):
        """Check if data is recent (not stale).

        Args:
            symbol: Trading symbol
            timeframe: Timeframe string
            max_age_hours: Maximum age threshold in hours

        Returns:
            Boolean indicating if data is fresh
        """
        try:
            tf_str = f"M{timeframe}" if timeframe < 60 else f"H{timeframe//60}"
            # Query market_data using direct symbol column (new schema, no JOIN needed)
            query = "SELECT MAX(md.time) as latest_time FROM market_data md WHERE md.symbol = ? AND md.timeframe = ?"
            result = self.db.conn.cursor().execute(query, (symbol, tf_str)).fetchone()

            if not result or not result[0]:
                self.logger.warning("No data found for %s (%s)", symbol, tf_str)
                return False

            latest_time = pd.to_datetime(result[0])
            age = datetime.now() - latest_time.replace(tzinfo=None)

            if age > timedelta(hours=max_age_hours):
                self.logger.warning(
                    "Stale data for %s (%s): %.1f hours old",
                    symbol,
                    tf_str,
                    age.total_seconds() / 3600,
                )
                return False

            self.logger.debug(
                "Fresh data for %s (%s): %.1f minutes old",
                symbol,
                tf_str,
                age.total_seconds() / 60,
            )
            return True
        except (RuntimeError, ValueError, KeyError) as e:
            self.logger.error("Error checking data freshness for %s: %s", symbol, e)
            return False

    def sync_backtest_data(self, symbol):
        """Sync market_data to backtest_market_data (no duplicates)"""
        try:
            tf_list = [
                p["timeframe"] for p in self.config["pairs"] if p["symbol"] == symbol
            ]

            for tf in tf_list:
                tf_str = f"M{tf}" if tf < 60 else f"H{tf//60}"

                # Read from market_data
                query = "SELECT md.* FROM market_data md JOIN tradable_pairs tp ON md.symbol_id = tp.id WHERE tp.symbol = ? AND md.timeframe = ? ORDER BY md.time ASC"
                data = pd.read_sql_query(query, self.db.conn, params=(symbol, tf_str))

                if data.empty:
                    self.logger.warning(
                        "No data in market_data for %s (%s)", symbol, tf_str
                    )
                    continue

                # Check for duplicates in backtest_market_data
                try:
                    existing = pd.read_sql_query(
                        "SELECT bmd.time FROM backtest_market_data bmd JOIN tradable_pairs tp ON bmd.symbol_id = tp.id WHERE tp.symbol = ? AND bmd.timeframe = ?",
                        self.db.conn,
                        params=(symbol, tf_str),
                    )
                    if not existing.empty:
                        data = data[~data["time"].isin(existing["time"])]
                except (RuntimeError, ValueError, KeyError):
                    pass

                if not data.empty:
                    data.to_sql(
                        "backtest_market_data",
                        self.db.conn,
                        if_exists="append",
                        index=False,
                    )
                    self.db.conn.commit()
                    self.logger.info(
                        "Synced %d rows to backtest_market_data for %s (%s)",
                        len(data),
                        symbol,
                        tf_str,
                    )
        except (RuntimeError, ValueError, KeyError) as e:
            self.logger.error("Failed to sync backtest data for %s: %s", symbol, e)
