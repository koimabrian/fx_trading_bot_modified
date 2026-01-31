"""Initialization manager for the FX Trading Bot.

Handles the 'init' mode which sets up the database, populates tradable pairs
from MT5, and fetches historical data for backtesting.
"""

# pylint: disable=no-member
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import MetaTrader5 as mt5
import pandas as pd

from src.utils.logging_factory import LoggingFactory


class InitManager:
    """Manages database initialization and historical data population."""

    def __init__(self, db, mt5_conn, config: Dict):
        """Initialize InitManager.

        Args:
            db: Database manager instance
            mt5_conn: MT5 connector instance
            config: Configuration dictionary
        """
        self.db = db
        self.mt5_conn = mt5_conn
        self.config = config
        self.logger = LoggingFactory.get_logger(__name__)
        self.sync_config = config.get("sync", {})
        self.min_rows_threshold = self.sync_config.get("min_rows_threshold", 1000)
        self.selected_symbols = []  # Will be populated by GUI or init flow

    def run_initialization(self) -> bool:
        """Execute the initialization workflow.

        Returns:
            True if successful, False otherwise
        """
        # Clear log file for clean initialization
        log_file = "logs/terminal_log.txt"
        if os.path.exists(log_file):
            try:
                os.remove(log_file)
            except OSError:
                pass  # If deletion fails, continue anyway

        self.logger.info("=" * 60)
        self.logger.info("INITIALIZATION MODE: Starting database setup...")
        self.logger.info("=" * 60)

        try:
            # Step 1: Validate configuration
            if not self._validate_config():
                return False

            # Step 2: Initialize MT5 connection
            if not self.mt5_conn.initialize():
                self.logger.error("Failed to initialize MT5 connection")
                return False

            # Step 3: Populate tradable_pairs table
            if not self._populate_tradable_pairs():
                return False

            # Step 4: Fetch historical data for all pairs
            if not self._fetch_historical_data():
                return False

            self.logger.info("=" * 60)
            self.logger.info("INITIALIZATION COMPLETE")
            self.logger.info("=" * 60)
            return True

        except (OSError, ValueError, KeyError) as e:
            self.logger.error("Initialization failed: %s", e)
            return False

    def _validate_config(self) -> bool:
        """Validate required configuration settings.

        Returns:
            True if valid, False otherwise
        """
        required_keys = ["mt5", "database", "timeframes"]
        missing_keys = [k for k in required_keys if k not in self.config]

        if missing_keys:
            self.logger.error("Missing required config keys: %s", missing_keys)
            return False

        mt5_config = self.config.get("mt5", {})
        required_mt5_keys = ["login", "password", "server"]
        missing_mt5_keys = [k for k in required_mt5_keys if not mt5_config.get(k)]

        if missing_mt5_keys:
            self.logger.error("Missing required MT5 config: %s", missing_mt5_keys)
            return False

        self.logger.info("Configuration validation passed")
        return True

    def _populate_tradable_pairs(self) -> bool:
        """Fetch all available symbols from MT5 and launch pair selector dialog.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Fetching all available symbols from MT5...")

            # Get all symbols from MT5
            all_symbols = mt5.symbols_get(
                group="*"
            )  # pylint: disable=no-member # type: ignore
            if not all_symbols:
                self.logger.error("Failed to fetch symbols from MT5")
                return False

            # Filter tradable pairs (full trading mode)
            tradable_symbols = [
                s.name
                for s in all_symbols
                if hasattr(s, "trade_mode")
                and s.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL
            ]

            self.logger.info(
                "Found %d tradable symbols, %d total",
                len(tradable_symbols),
                len(all_symbols),
            )

            # If selected_symbols already set (by GUI wizard), use them
            if self.selected_symbols:
                selected_pairs = self.selected_symbols
                self.logger.info(
                    "Using pre-selected symbols from GUI: %d pairs",
                    len(selected_pairs),
                )
            else:
                # Fall back to dialog-based selection
                # This path is for non-GUI init (backward compatibility)
                selected_pairs = tradable_symbols
                self.logger.info(
                    "No pre-selected symbols. Using all %d tradable symbols",
                    len(selected_pairs),
                )

            # Clear tradable_pairs table for fresh initialization
            cursor = self.db.conn.cursor()
            cursor.execute("DELETE FROM tradable_pairs")
            self.db.conn.commit()
            self.logger.info("Cleared tradable_pairs table")

            # Insert selected pairs into tradable_pairs table
            inserted = 0

            for symbol in selected_pairs:
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO tradable_pairs (symbol) VALUES (?)",
                        (symbol,),
                    )
                    inserted += 1
                except (ValueError, OSError) as e:
                    self.logger.debug("Could not insert symbol %s: %s", symbol, e)

            self.db.conn.commit()
            self.logger.info(
                "Inserted %d selected symbols into tradable_pairs table", inserted
            )
            return True

        except (OSError, ValueError) as e:
            self.logger.error("Failed to populate tradable_pairs: %s", e)
            return False

    def _fetch_historical_data(self) -> bool:
        """Fetch historical data for all selected pairs and timeframes.

        Returns:
            True if successful, False otherwise
        """
        try:
            from src.core.data_fetcher import DataFetcher

            data_fetcher = DataFetcher(self.mt5_conn, self.db, self.config)

            # Get selected pairs from tradable_pairs table (not config)
            symbols = self.db.get_all_symbols()

            if not symbols:
                self.logger.error("No symbols found in tradable_pairs table")
                return False

            timeframes = self.config.get("timeframes", [15, 60, 240])

            self.logger.info(
                "Fetching historical data for %d symbols × %d timeframes...",
                len(symbols),
                len(timeframes),
            )

            # Get date range from config
            start_date_str = self.sync_config.get("start_date", "2023-01-01")
            end_date_str = self.sync_config.get(
                "end_date", datetime.now().strftime("%Y-%m-%d")
            )

            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            except ValueError:
                self.logger.warning("Invalid date format in config, using last 2 years")
                end_date = datetime.now()
                start_date = end_date - timedelta(days=730)

            self.logger.info(
                "Historical data date range: %s to %s",
                start_date.date(),
                end_date.date(),
            )

            # Fetch data for each symbol/timeframe
            total_rows = 0
            skipped_pairs = 0

            for symbol in symbols:
                for timeframe in timeframes:
                    try:
                        rows_added = data_fetcher.sync_data_for_pair(
                            symbol=symbol,
                            timeframe=timeframe,
                            start_date=start_date,
                            end_date=end_date,
                        )

                        if rows_added >= self.min_rows_threshold:
                            self.logger.info(
                                "  %s (%d min): %d rows loaded",
                                symbol,
                                timeframe,
                                rows_added,
                            )
                            total_rows += rows_added
                        else:
                            self.logger.warning(
                                "  %s (%d min): Only %d rows (need %d minimum)",
                                symbol,
                                timeframe,
                                rows_added,
                                self.min_rows_threshold,
                            )
                            skipped_pairs += 1

                    except Exception as e:
                        self.logger.warning(
                            "Failed to fetch data for %s (%d min): %s",
                            symbol,
                            timeframe,
                            e,
                        )
                        skipped_pairs += 1

            self.logger.info(
                "Historical data fetch complete: %d rows loaded, %d pairs skipped",
                total_rows,
                skipped_pairs,
            )

            return total_rows > 0

        except Exception as e:
            self.logger.error("Failed to fetch historical data: %s", e)
            return False
