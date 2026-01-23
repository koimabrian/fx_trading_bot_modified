"""Market data fetching and synchronization.

Retrieves OHLCV data from MT5, syncs to database, and provides
data validation and caching interfaces for strategy backtesting.
"""

import logging
import sqlite3
import threading
from typing import Dict, Optional

import MetaTrader5 as mt5
import pandas as pd


class DataFetcher:
    """Fetches and syncs market data from MT5 or database."""

    def __init__(self, mt5_conn, db, config=None):
        """Initialize DataFetcher.

        Args:
            mt5_conn: MT5 connector instance
            db: Database manager instance
            config: Configuration dictionary
        """
        self.mt5_conn = mt5_conn
        self.db = db
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.pairs = self.load_pairs()

    def load_pairs(self):
        """Load trading pairs from config"""
        try:
            return self.config.get("pairs", [])
        except (KeyError, AttributeError) as e:
            self.logger.error("Failed to load pairs from config: %s", e)
            return []

    def has_sufficient_data(
        self, min_rows: int = 2000, table: str = "market_data", symbol: str = None
    ) -> bool:
        """Check if configured pairs per timeframe have sufficient data in the database.

        Args:
            min_rows: Minimum number of rows per pair per timeframe (default 2000 from config)
            table: Table to check ('market_data' only)
            symbol: Optional specific symbol to check and its timeframes. If None, checks all pairs.

        Returns:
            Boolean indicating if all checked pairs have >= min_rows
        """
        try:
            if not self.pairs:
                self.logger.warning("No pairs configured")
                return False

            insufficient_pairs = []

            # Filter pairs by symbol if specified
            pairs_to_check = (
                [p for p in self.pairs if p["symbol"] == symbol]
                if symbol
                else self.pairs
            )

            for pair in pairs_to_check:
                sym = pair["symbol"]
                tf = pair["timeframe"]
                tf_str = f"M{tf}" if tf < 60 else f"H{tf // 60}"

                # Query row count for this pair
                query = f"SELECT COUNT(*) as count FROM {table} WHERE symbol = ? AND timeframe = ?"
                result = self.db.execute_query(query, (sym, tf_str))

                if result:
                    row_count = result[0]["count"]
                    if row_count < min_rows:
                        insufficient_pairs.append(
                            f"{sym} ({tf_str}): {row_count}/{min_rows} rows"
                        )
                else:
                    insufficient_pairs.append(f"{sym} ({tf_str}): 0/{min_rows} rows")

            if insufficient_pairs:
                self.logger.debug(
                    "Insufficient data in %s table: %s",
                    table,
                    ", ".join(insufficient_pairs[:3]),  # Log first 3 for brevity
                )
                return False

            self.logger.debug(
                "All %d pairs have sufficient data (>= %d rows) in %s table",
                len(pairs_to_check),
                min_rows,
                table,
            )
            return True

        except (sqlite3.Error, KeyError, ValueError) as e:
            self.logger.error("Error checking data sufficiency: %s", e)
            return False

    def fetch_data(
        self, symbol, timeframe, limit=None, table="market_data", required_rows=None
    ):
        """Fetch data from database or MT5.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe in minutes or string format (e.g., 'M15', 'H1', etc.)
            limit: Maximum rows to fetch (uses config if None)
            table: Table name ('market_data' or 'backtest_market_data')
            required_rows: Minimum rows needed for indicator calculation.
                          If provided, fetches required_rows * 1.1 (with buffer)
                          Otherwise uses config fetch_limit

        Returns:
            DataFrame with market data or empty DataFrame on error
        """
        if required_rows is not None:
            # Fetch only what's needed + 10% buffer for edge cases
            limit = int(required_rows * 1.1)
            self.logger.debug(
                "Smart fetch limit for %s: %d rows (required: %d + buffer)",
                symbol,
                limit,
                required_rows,
            )
        else:
            limit = limit or self.config.get("data", {}).get("fetch_limit", 1000)
        # Convert timeframe to int if it's a string (e.g., 'M15' -> 15, 'H1' -> 60)
        if isinstance(timeframe, str):
            if timeframe.startswith("H"):
                timeframe = int(timeframe[1:]) * 60
            elif timeframe.startswith("M"):
                timeframe = int(timeframe[1:])
        # Ensure timeframe is a string (e.g., 'M15', 'H1') for database queries
        tf_str = f"M{timeframe}" if timeframe < 60 else f"H{timeframe//60}"
        try:
            query = f"SELECT * FROM {table} WHERE symbol = ? AND timeframe = ? ORDER BY time DESC LIMIT ?"
            data = pd.read_sql(query, self.db.conn, params=(symbol, tf_str, limit))
            if data.empty:
                self.logger.warning(
                    "No data in %s for %s (%s), fetching from MT5",
                    table,
                    symbol,
                    tf_str,
                )
                mt5_timeframe = getattr(mt5, f"TIMEFRAME_{tf_str}", mt5.TIMEFRAME_M15)
                self.sync_data(symbol, timeframe, mt5_timeframe, table)
                data = pd.read_sql(query, self.db.conn, params=(symbol, tf_str, limit))
            self.logger.info(
                "Fetched %s rows from %s for %s (%s)", len(data), table, symbol, tf_str
            )
            return data
        except (pd.errors.DatabaseError, ValueError) as e:
            self.logger.error("Failed to fetch data for %s (%s): %s", symbol, tf_str, e)
            return pd.DataFrame()

    def sync_data(
        self, symbol=None, timeframe=None, mt5_timeframe=None, table="market_data"
    ) -> None:
        """Fetch and sync OHLCV market data for all configured pairs or specific symbol/timeframe.
        Supports separate tables (market_data for live, backtest_market_data for backtesting).
        Deduplicates based on time to avoid duplicates.
        """
        if not self.mt5_conn:
            self.logger.error("MT5 connector not provided")
            return
        if not self.mt5_conn.initialize():
            self.logger.error(
                "Failed to initialize MT5 connection. Ensure MetaTrader 5 terminal is running and credentials in config.yaml are correct."
            )
            return

        # If symbol is specified, filter pairs to only those matching that symbol
        if symbol:
            pairs_to_sync = [p for p in self.pairs if p["symbol"] == symbol]
        else:
            pairs_to_sync = self.pairs
        for pair in pairs_to_sync:
            if isinstance(pair, tuple):
                sym, tf, mt5_tf = pair
            else:
                sym = pair["symbol"]
                tf = pair["timeframe"]
                mt5_tf = pair.get("mt5_timeframe", mt5_timeframe)

            # Convert numeric timeframe to MT5 constant if needed
            if mt5_tf is None and tf is not None:
                # Map numeric timeframe (15, 60, 240) to MT5 constant
                tf_map = {
                    15: mt5.TIMEFRAME_M15,
                    60: mt5.TIMEFRAME_H1,
                    240: mt5.TIMEFRAME_H4,
                }
                mt5_tf = tf_map.get(tf, mt5.TIMEFRAME_M15)
                self.logger.debug(
                    "Converted timeframe %s to MT5 constant for %s", tf, sym
                )

            tf_str = f"M{tf}" if tf < 60 else f"H{tf//60}"

            self.logger.debug(
                "Starting data sync for %s (%s) -> %s", sym, tf_str, table
            )
            fetch_count = self.config.get("data", {}).get("fetch_count", 2000)
            data = self.mt5_conn.fetch_market_data(sym, mt5_tf, count=fetch_count)
            if data is None or data.empty:
                self.logger.warning(
                    "No data fetched for %s (%s). Symbol may not be in MT5 Market Watch.",
                    sym,
                    tf_str,
                )
                continue

            try:
                # Ensure we have OHLCV columns
                required_cols = ["time", "open", "high", "low", "close", "tick_volume"]
                for col in required_cols:
                    if col not in data.columns:
                        self.logger.warning(
                            "Column '%s' missing from fetched data for %s. Adding as NaN.",
                            col,
                            sym,
                        )
                        data[col] = None

                data["symbol"] = sym
                data["timeframe"] = tf_str

                # Check for duplicates in target table
                try:
                    existing_data = pd.read_sql(
                        f"SELECT time FROM {table} WHERE symbol = ? AND timeframe = ?",
                        self.db.conn,
                        params=(sym, tf_str),
                    )
                    self.logger.debug(
                        "Found %s existing rows for %s (%s) in %s",
                        len(existing_data),
                        sym,
                        tf_str,
                        table,
                    )
                    if not existing_data.empty:
                        # Ensure time columns are the same dtype before comparison
                        existing_data["time"] = pd.to_datetime(existing_data["time"])
                        data["time"] = pd.to_datetime(data["time"])
                        data = data[~data["time"].isin(existing_data["time"])]
                        self.logger.debug(
                            "After deduplication, %s new rows remain for %s (%s)",
                            len(data),
                            sym,
                            tf_str,
                        )
                except (pd.errors.DatabaseError, ValueError) as e:
                    self.logger.debug(
                        "Table %s may not exist yet, will create: %s", table, e
                    )

                if not data.empty:
                    data.to_sql(table, self.db.conn, if_exists="append", index=False)
                    self.db.conn.commit()
                    self.logger.info(
                        "Synced %s new rows for %s (%s) to %s",
                        len(data),
                        sym,
                        tf_str,
                        table,
                    )
                else:
                    self.logger.info("No new data to sync for %s (%s)", sym, tf_str)
            except (pd.errors.DatabaseError, ValueError) as e:
                self.logger.error("Failed to sync data for %s (%s): %s", sym, tf_str, e)
            finally:
                self.logger.debug(
                    "Completed data sync attempt for %s (%s)", sym, tf_str
                )

    def sync_data_incremental(
        self, symbol=None, timeframe=None, mt5_timeframe=None, table="market_data"
    ) -> None:
        """Incremental data sync: only fetch data newer than the last timestamp in the database.

        This is optimized for live trading - only fetches the minimal data needed to stay current.
        Much faster than full syncs and reduces MT5 API load.
        """
        if not self.mt5_conn:
            self.logger.error("MT5 connector not provided")
            return
        if not self.mt5_conn.initialize():
            self.logger.error(
                "Failed to initialize MT5 connection. Ensure MetaTrader 5 terminal is running."
            )
            return

        # Filter pairs by symbol if specified (consistent with sync_data())
        if symbol:
            pairs_to_sync = [p for p in self.pairs if p["symbol"] == symbol]
        else:
            pairs_to_sync = self.pairs
        for pair in pairs_to_sync:
            sym = pair["symbol"]
            tf = pair["timeframe"]
            mt5_tf = pair.get("mt5_timeframe", mt5_timeframe)

            # Convert numeric timeframe (15, 60, 240) to MT5 constant if needed
            if mt5_tf is None and tf is not None:
                # Map numeric timeframe to MT5 constant
                tf_map = {
                    15: mt5.TIMEFRAME_M15,
                    60: mt5.TIMEFRAME_H1,
                    240: mt5.TIMEFRAME_H4,
                }
                mt5_tf = tf_map.get(tf, mt5.TIMEFRAME_M15)
                self.logger.debug(
                    "Converted timeframe %s to MT5 constant for %s", tf, sym
                )

            tf_str = f"M{tf}" if tf < 60 else f"H{tf//60}"

            try:
                # Get the latest timestamp from the database
                query = f"SELECT MAX(time) as latest_time FROM {table} WHERE symbol = ? AND timeframe = ?"
                result = self.db.execute_query(query, (sym, tf_str))

                latest_time = None
                if result and result[0]["latest_time"]:
                    latest_time = pd.to_datetime(result[0]["latest_time"])
                    self.logger.debug(
                        "Latest data for %s (%s): %s", sym, tf_str, latest_time
                    )

                # Fetch only the last 100 candles (covers ~1-7 days depending on timeframe)
                fetch_count = 100
                data = self.mt5_conn.fetch_market_data(sym, mt5_tf, count=fetch_count)

                if data is None or data.empty:
                    self.logger.warning("No new data fetched for %s (%s)", sym, tf_str)
                    continue

                # If we have a latest timestamp, filter to only newer data
                if latest_time is not None:
                    data["time"] = pd.to_datetime(data["time"])
                    data = data[data["time"] > latest_time]
                    self.logger.debug(
                        "After filtering by timestamp, %d new rows for %s (%s)",
                        len(data),
                        sym,
                        tf_str,
                    )

                if data.empty:
                    self.logger.info("No new data to sync for %s (%s)", sym, tf_str)
                    continue

                # Add required columns
                data["symbol"] = sym
                data["timeframe"] = tf_str

                # Ensure we have required columns
                required_cols = ["time", "open", "high", "low", "close", "tick_volume"]
                for col in required_cols:
                    if col not in data.columns:
                        data[col] = None

                # Insert new data
                data.to_sql(table, self.db.conn, if_exists="append", index=False)
                self.db.conn.commit()
                self.logger.info(
                    "Synced %d new rows for %s (%s) (incremental)",
                    len(data),
                    sym,
                    tf_str,
                )

            except (pd.errors.DatabaseError, ValueError) as e:
                self.logger.error(
                    "Incremental sync failed for %s (%s): %s", sym, tf_str, e
                )
            finally:
                self.logger.debug(
                    "Completed incremental sync attempt for %s (%s)", sym, tf_str
                )
