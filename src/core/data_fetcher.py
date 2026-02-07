"""Market data fetching and synchronization.

Retrieves OHLCV data from MT5, syncs to database, and provides
data validation and caching interfaces for strategy backtesting.
Uses LRU cache to avoid redundant fetches.
"""

import sqlite3
from functools import lru_cache
from typing import Optional

import MetaTrader5 as mt5
import pandas as pd

from src.utils.logging_factory import LoggingFactory


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
        self.logger = LoggingFactory.get_logger(__name__)
        self.pairs = self.load_pairs()

    def load_pairs(self):
        """Load trading pairs from database tradable_pairs table.

        Returns:
            List of dicts with 'symbol' and 'timeframe' keys for each
            symbol/timeframe combination, or empty list on error.
        """
        try:
            if hasattr(self, "db") and self.db:
                cursor = self.db.conn.cursor()
                cursor.execute("SELECT symbol FROM tradable_pairs ORDER BY symbol")
                symbols = [row[0] for row in cursor.fetchall()]

                # Get timeframes from config
                timeframes = self.config.get("timeframes", [15, 60, 240])

                # Create pairs list with symbol and timeframe combination
                pairs = []
                for symbol in symbols:
                    for timeframe in timeframes:
                        pairs.append({"symbol": symbol, "timeframe": timeframe})

                return pairs
            return []
        except (KeyError, AttributeError) as e:
            self.logger.error("Failed to load pairs from database: %s", e)
            return []

    def has_sufficient_data(
        self, min_rows: int = 2000, symbol: Optional[str] = None
    ) -> bool:
        """Check if configured pairs per timeframe have sufficient data in the database.

        Args:
            min_rows: Minimum number of rows per pair per timeframe (default 2000 from config)
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

                # Query row count for this pair (unified market_data table with direct symbol column)
                query = "SELECT COUNT(*) as count FROM market_data WHERE symbol = ? AND timeframe = ?"
                cursor = self.db.execute_query(query, (sym, tf_str))
                result = cursor.fetchone()

                if result:
                    row_count = result["count"]
                    if row_count < min_rows:
                        insufficient_pairs.append(
                            f"{sym} ({tf_str}): {row_count}/{min_rows} rows"
                        )
                else:
                    insufficient_pairs.append(f"{sym} ({tf_str}): 0/{min_rows} rows")

            if insufficient_pairs:
                self.logger.debug(
                    "Insufficient data in market_data table: %s",
                    ", ".join(insufficient_pairs[:3]),  # Log first 3 for brevity
                )
                return False

            self.logger.debug(
                "All %d pairs have sufficient data (>= %d rows) in market_data table",
                len(pairs_to_check),
                min_rows,
            )
            return True

        except (sqlite3.Error, KeyError, ValueError) as e:
            self.logger.error("Error checking data sufficiency: %s", e)
            return False

    @lru_cache(maxsize=128)
    def _get_market_data_cached(self, symbol: str, timeframe_str: str, limit: int):
        """Cached fetch of market data to avoid redundant queries.

        Args:
            symbol: Trading symbol (must be string for caching)
            timeframe_str: Formatted timeframe string (e.g., 'M15', 'H1')
            limit: Maximum rows to fetch

        Returns:
            Tuple of (data_list, count) to make it hashable for caching
        """
        query = "SELECT * FROM market_data WHERE symbol = ? AND timeframe = ? ORDER BY time DESC LIMIT ?"
        data = pd.read_sql(query, self.db.conn, params=(symbol, timeframe_str, limit))
        # Convert to tuple of records for hashability
        return (tuple(data.to_dict("records")), len(data))

    def fetch_data(self, symbol, timeframe, limit=None, required_rows=None):
        """Fetch data from database or MT5.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe in minutes or string format (e.g., 'M15', 'H1', etc.)
            limit: Maximum rows to fetch (uses config if None)
            required_rows: Minimum rows needed for indicator calculation.
                          If provided, calculates dynamic limit based on:
                          - 3x multiplier for safety margin
                          - Minimum from config (data.min_fetch_buffer)
                          Otherwise uses config fetch_limit

        Returns:
            DataFrame with market data or empty DataFrame on error
        """
        if required_rows is not None:
            # Calculate dynamic fetch limit based on strategy requirements
            # Use config value for minimum buffer if available
            min_buffer = self.config.get("data", {}).get("min_fetch_buffer", 50)
            multiplier = self.config.get("data", {}).get("fetch_multiplier", 3)

            # Ensure we fetch enough for signal reliability:
            # - Base calculation: required_rows * multiplier
            # - Minimum fallback: required_rows + buffer
            limit = max(required_rows + min_buffer, int(required_rows * multiplier))

            self.logger.debug(
                "Calculated fetch limit for %s: %d rows (required: %d, buffer: %d, multiplier: %.1fx)",
                symbol,
                limit,
                required_rows,
                min_buffer,
                multiplier,
            )
        else:
            limit = limit or self.config.get("data", {}).get("fetch_limit", 1000)
        # Convert timeframe to int if it's a string (e.g., 'M15' -> 15, 'H1' -> 60)
        timeframe_int = timeframe
        if isinstance(timeframe, str):
            if timeframe.startswith("H"):
                timeframe_int = int(timeframe[1:]) * 60
            elif timeframe.startswith("M"):
                timeframe_int = int(timeframe[1:])
        else:
            timeframe_int = int(timeframe)
        # Ensure timeframe is a string (e.g., 'M15', 'H1') for database queries
        tf_str = f"M{timeframe_int}" if timeframe_int < 60 else f"H{timeframe_int//60}"
        try:
            # Check existing row count before fetching from MT5
            count_query = "SELECT COUNT(*) as count FROM market_data WHERE symbol = ? AND timeframe = ?"
            cursor = self.db.execute_query(count_query, (symbol, tf_str))
            count_result = cursor.fetchone()
            existing_count = count_result["count"] if count_result else 0

            # Use cached fetch to avoid redundant queries
            data_records, data_count = self._get_market_data_cached(
                symbol, tf_str, limit
            )
            data = pd.DataFrame(list(data_records)) if data_records else pd.DataFrame()

            if data.empty and existing_count == 0:
                self.logger.warning(
                    "No data in market_data for %s (%s), fetching from MT5",
                    symbol,
                    tf_str,
                )
                mt5_timeframe = getattr(mt5, f"TIMEFRAME_{tf_str}", mt5.TIMEFRAME_M15)
                self.sync_data(symbol=symbol, mt5_timeframe=mt5_timeframe)
                # Clear cache after sync
                self._get_market_data_cached.cache_clear()
                # Re-fetch with cache
                data_records, data_count = self._get_market_data_cached(
                    symbol, tf_str, limit
                )
                data = (
                    pd.DataFrame(list(data_records)) if data_records else pd.DataFrame()
                )

            self.logger.debug(
                "Fetched %s rows from market_data for %s (%s) [%s total in DB]",
                len(data),
                symbol,
                tf_str,
                existing_count,
            )
            return data
        except (pd.errors.DatabaseError, ValueError) as e:
            self.logger.error("Failed to fetch data for %s (%s): %s", symbol, tf_str, e)
            return pd.DataFrame()

    def sync_data(self, symbol=None, mt5_timeframe=None) -> None:
        """Fetch and sync OHLCV market data for all configured pairs or specific symbol.

        Uses unified market_data table with composite primary key.
        Automatically handles duplicates via INSERT OR IGNORE.

        Args:
            symbol: Optional specific symbol to sync. If None, syncs all pairs.
            mt5_timeframe: Optional MT5 timeframe constant override.

        Returns:
            None. Data is written to database.
        """ ""
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
                "Starting data sync for %s (%s) -> market_data", sym, tf_str
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

                # Format time as ISO format string
                data["time"] = pd.to_datetime(data["time"]).dt.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                # Extract OHLCV columns we need
                data_prepared = pd.DataFrame(
                    {
                        "time": data["time"],
                        "symbol": sym,
                        "timeframe": tf_str,
                        "open": data["open"],
                        "high": data["high"],
                        "low": data["low"],
                        "close": data["close"],
                        "tick_volume": data.get("tick_volume", 0),
                        "spread": data.get("spread", None),
                        "real_volume": data.get("real_volume", 0),
                    }
                )

                if not data_prepared.empty:
                    # Prepare rows for INSERT OR IGNORE
                    rows = []
                    for _, row in data_prepared.iterrows():
                        rows.append(
                            (
                                row["time"],
                                row["symbol"],
                                row["timeframe"],
                                row["open"],
                                row["high"],
                                row["low"],
                                row["close"],
                                row["tick_volume"],
                                row["spread"],
                                row["real_volume"],
                            )
                        )

                    # Use INSERT OR IGNORE to handle duplicates gracefully
                    query = """
                    INSERT OR IGNORE INTO market_data 
                    (time, symbol, timeframe, open, high, low, close, tick_volume, spread, real_volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                    cursor = self.db.conn.cursor()
                    cursor.executemany(query, rows)
                    self.db.conn.commit()

                    # Count how many rows were actually inserted (duplicates ignored)
                    inserted_count = cursor.rowcount
                    self.logger.info(
                        "Synced %s rows for %s (%s) to market_data (duplicates ignored)",
                        inserted_count,
                        sym,
                        tf_str,
                    )
                else:
                    self.logger.info("No new data to sync for %s (%s)", sym, tf_str)

            except (sqlite3.Error, ValueError) as e:
                self.logger.error("Failed to sync data for %s (%s): %s", sym, tf_str, e)
                self.db.conn.rollback()
            finally:
                self.logger.debug(
                    "Completed data sync attempt for %s (%s)", sym, tf_str
                )

    def sync_data_incremental(self, symbol=None, mt5_timeframe=None) -> None:
        """Incremental data sync: only fetch data newer than last timestamp.

        Optimized for live trading - only fetches minimal data needed.
        Uses unified market_data table with composite primary key.
        Much faster than full syncs and reduces MT5 API load.

        Args:
            symbol: Optional specific symbol to sync. If None, syncs all pairs.
            mt5_timeframe: Optional MT5 timeframe constant override.

        Returns:
            None. Data is written to database.
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
                # Get the latest timestamp from the unified market_data table
                query = "SELECT MAX(time) as latest_time FROM market_data WHERE symbol = ? AND timeframe = ?"
                cursor = self.db.conn.cursor()
                cursor.execute(query, (sym, tf_str))
                result = cursor.fetchone()

                latest_time = None
                if result and result[0]:
                    latest_time = pd.to_datetime(result[0])
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

                # Format time as ISO format string
                data["time"] = pd.to_datetime(data["time"]).dt.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                # Extract OHLCV columns we need
                data_prepared = pd.DataFrame(
                    {
                        "time": data["time"],
                        "symbol": sym,
                        "timeframe": tf_str,
                        "open": data["open"],
                        "high": data["high"],
                        "low": data["low"],
                        "close": data["close"],
                        "tick_volume": data.get("tick_volume", 0),
                        "spread": data.get("spread", None),
                        "real_volume": data.get("real_volume", 0),
                    }
                )

                # Prepare rows for INSERT OR IGNORE
                rows = []
                for _, row in data_prepared.iterrows():
                    rows.append(
                        (
                            row["time"],
                            row["symbol"],
                            row["timeframe"],
                            row["open"],
                            row["high"],
                            row["low"],
                            row["close"],
                            row["tick_volume"],
                            row["spread"],
                            row["real_volume"],
                        )
                    )

                # Use INSERT OR IGNORE to handle duplicates gracefully
                query = """
                INSERT OR IGNORE INTO market_data 
                (time, symbol, timeframe, open, high, low, close, tick_volume, spread, real_volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                cursor.executemany(query, rows)
                self.db.conn.commit()

                # Count how many rows were actually inserted (duplicates ignored)
                inserted_count = cursor.rowcount
                self.logger.info(
                    "Synced %d new rows for %s (%s) (incremental, duplicates ignored)",
                    inserted_count,
                    sym,
                    tf_str,
                )

            except (sqlite3.Error, ValueError) as e:
                self.logger.error(
                    "Incremental sync failed for %s (%s): %s", sym, tf_str, e
                )
                self.db.conn.rollback()
            finally:
                self.logger.debug(
                    "Completed incremental sync attempt for %s (%s)", sym, tf_str
                )

    def sync_data_for_pair(
        self,
        symbol: str,
        timeframe: int,
        start_date,
        end_date,
    ) -> int:
        """Synchronize data for a single pair (used by init mode).

        Uses unified market_data table with composite primary key.
        Automatically handles duplicates via INSERT OR IGNORE.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe in minutes
            start_date: Start date for historical data
            end_date: End date for historical data

        Returns:
            Number of rows added
        """
        tf_str = None
        try:
            tf_str = self.format_timeframe(timeframe)

            # Convert start_date and end_date to datetime if needed
            if isinstance(start_date, str):
                from datetime import datetime

                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            if isinstance(end_date, str):
                from datetime import datetime

                end_date = datetime.strptime(end_date, "%Y-%m-%d")

            # Fetch data from MT5
            timeframe_mt5 = self.get_mt5_timeframe(timeframe)
            data = self.mt5_conn.fetch_market_data(symbol, timeframe_mt5, count=2000)

            if data is None or data.empty:
                self.logger.warning("No data available for %s (%s)", symbol, tf_str)
                return 0

            # Format time as ISO format string
            data["time"] = pd.to_datetime(data["time"]).dt.strftime("%Y-%m-%d %H:%M:%S")

            # Extract OHLCV columns we need
            data_prepared = pd.DataFrame(
                {
                    "time": data["time"],
                    "symbol": symbol,
                    "timeframe": tf_str,
                    "open": data["open"],
                    "high": data["high"],
                    "low": data["low"],
                    "close": data["close"],
                    "tick_volume": data.get("tick_volume", 0),
                    "spread": data.get("spread", None),
                    "real_volume": data.get("real_volume", 0),
                }
            )

            # Prepare rows for INSERT OR IGNORE
            rows = []
            for _, row in data_prepared.iterrows():
                rows.append(
                    (
                        row["time"],
                        row["symbol"],
                        row["timeframe"],
                        row["open"],
                        row["high"],
                        row["low"],
                        row["close"],
                        row["tick_volume"],
                        row["spread"],
                        row["real_volume"],
                    )
                )

            # Use INSERT OR IGNORE to handle duplicates gracefully
            query = """
            INSERT OR IGNORE INTO market_data 
            (time, symbol, timeframe, open, high, low, close, tick_volume, spread, real_volume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor = self.db.conn.cursor()
            cursor.executemany(query, rows)
            self.db.conn.commit()

            rows_added = cursor.rowcount
            self.logger.info(
                "Added %d rows for %s (%s) from %s to %s (duplicates ignored)",
                rows_added,
                symbol,
                tf_str,
                start_date.date(),
                end_date.date(),
            )

            return rows_added

        except (OSError, ValueError, sqlite3.Error) as e:
            self.logger.error(
                "Failed to sync data for %s (%s): %s", symbol, tf_str or "?", e
            )
            return 0

    def format_timeframe(self, timeframe_minutes: int) -> str:
        """Convert timeframe from minutes to string format.

        Args:
            timeframe_minutes: Timeframe in minutes

        Returns:
            Formatted timeframe string (e.g., 'M15', 'H1')
        """
        if timeframe_minutes < 60:
            return f"M{timeframe_minutes}"
        elif timeframe_minutes < 1440:
            return f"H{timeframe_minutes // 60}"
        else:
            return f"D{timeframe_minutes // 1440}"

    def get_mt5_timeframe(self, timeframe_minutes: int):
        """Get MT5 timeframe enum from minutes.

        Args:
            timeframe_minutes: Timeframe in minutes

        Returns:
            MT5 timeframe constant
        """
        timeframe_map = {
            1: mt5.TIMEFRAME_M1,
            5: mt5.TIMEFRAME_M5,
            15: mt5.TIMEFRAME_M15,
            30: mt5.TIMEFRAME_M30,
            60: mt5.TIMEFRAME_H1,
            240: mt5.TIMEFRAME_H4,
            1440: mt5.TIMEFRAME_D1,
            10080: mt5.TIMEFRAME_W1,
            43200: mt5.TIMEFRAME_MN1,
        }
        return timeframe_map.get(timeframe_minutes, mt5.TIMEFRAME_M15)
