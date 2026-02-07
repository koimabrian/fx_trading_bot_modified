"""Database schema migrations for the FX Trading Bot.

Handles creation and evolution of database tables to support the hybrid
workflow including tradable_pairs, optimal_parameters, and comprehensive
backtest result storage with metrics and trading history.
"""

import logging
import sqlite3


class DatabaseMigrations:
    """Manages database schema creation and migrations."""

    def __init__(self, db_connection):
        """Initialize DatabaseMigrations.

        Args:
            db_connection: SQLite connection object
        """
        self.conn = db_connection
        self.logger = logging.getLogger(__name__)

    def create_tables(self) -> bool:
        """Create all required database tables.

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()

            # Table 1: tradable_pairs
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tradable_pairs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Table 2: market_data (unified for live and backtest) with composite primary key
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS market_data (
                    time TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    tick_volume INTEGER,
                    spread REAL,
                    real_volume INTEGER,
                    PRIMARY KEY (time, symbol, timeframe)
                )
            """
            )

            # Table 4: optimal_parameters - with FK to tradable_pairs
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS optimal_parameters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol_id INTEGER NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    parameter_value TEXT NOT NULL,
                    metrics TEXT,
                    last_optimized TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (symbol_id) REFERENCES tradable_pairs(id),
                    UNIQUE(symbol_id, timeframe, strategy_name)
                )
            """
            )

            # Table 5: backtest_backtests (comprehensive backtest metrics with JSON storage)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS backtest_backtests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id INTEGER NOT NULL,
                    symbol_id INTEGER NOT NULL,
                    timeframe TEXT NOT NULL,
                    metrics TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (strategy_id) REFERENCES backtest_strategies(id),
                    FOREIGN KEY (symbol_id) REFERENCES tradable_pairs(id),
                    UNIQUE(strategy_id, symbol_id, timeframe)
                )
            """
            )

            # Table 6: backtest_trades (individual trades from backtests) - with FK update
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS backtest_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backtest_result_id INTEGER,
                    backtest_backtest_id INTEGER,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT NOT NULL,
                    symbol_id INTEGER NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    volume REAL NOT NULL,
                    profit REAL NOT NULL,
                    profit_pct REAL NOT NULL,
                    duration_hours REAL,
                    FOREIGN KEY (backtest_result_id) REFERENCES backtest_results(id),
                    FOREIGN KEY (backtest_backtest_id) REFERENCES backtest_backtests(id),
                    FOREIGN KEY (symbol_id) REFERENCES tradable_pairs(id)
                )
            """
            )

            # Table 7: trades (live trading audit trail) - with FK to tradable_pairs
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol_id INTEGER NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    trade_type TEXT NOT NULL,
                    volume REAL NOT NULL,
                    open_price REAL NOT NULL,
                    close_price REAL,
                    open_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    close_time TIMESTAMP,
                    profit REAL,
                    status TEXT DEFAULT 'open',
                    order_id INTEGER,
                    deal_id INTEGER,
                    ticket INTEGER,
                    magic INTEGER,
                    swap REAL DEFAULT 0,
                    commission REAL DEFAULT 0,
                    comment TEXT,
                    external BOOLEAN DEFAULT 0,
                    mt5_synced_at TIMESTAMP,
                    FOREIGN KEY (symbol_id) REFERENCES tradable_pairs(id)
                )
            """
            )

            # Table 8: backtest_strategies (strategy registry)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS backtest_strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR UNIQUE NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Table 9: backtest_results (legacy - kept for historical data)
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS backtest_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    backtest_date TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_profit_pct REAL,
                    return_pct REAL,
                    sharpe_ratio REAL,
                    sortino_ratio REAL,
                    calmar_ratio REAL,
                    max_drawdown_pct REAL,
                    profit_factor REAL,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    win_rate_pct REAL,
                    avg_win REAL,
                    avg_loss REAL,
                    pl_ratio REAL,
                    recovery_factor REAL,
                    rank_score REAL,
                    UNIQUE(symbol, strategy_name, timeframe, start_date, end_date, backtest_date)
                )
            """
            )

            self.conn.commit()
            self.logger.info("All database tables created successfully")
            return True

        except sqlite3.Error as e:
            self.logger.error("Failed to create database tables: %s", e)
            return False

    def create_indexes(self) -> bool:
        """Create indexes for query performance optimization.

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()

            indexes = [
                # Market data indexes (unified table without foreign key)
                "CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timeframe ON market_data(symbol, timeframe)",
                "CREATE INDEX IF NOT EXISTS idx_market_data_time ON market_data(time DESC)",
                # Backtest backtests indexes (for new schema)
                "CREATE INDEX IF NOT EXISTS idx_backtest_backtests_strategy_symbol ON backtest_backtests(strategy_id, symbol_id)",
                "CREATE INDEX IF NOT EXISTS idx_backtest_backtests_symbol_timeframe ON backtest_backtests(symbol_id, timeframe)",
                "CREATE INDEX IF NOT EXISTS idx_backtest_backtests_timestamp ON backtest_backtests(timestamp DESC)",
                # Legacy backtest result indexes (if backtest_results still exists)
                "CREATE INDEX IF NOT EXISTS idx_backtest_results_symbol_timeframe ON backtest_results(symbol, timeframe, rank_score DESC)",
                "CREATE INDEX IF NOT EXISTS idx_backtest_results_strategy_rank ON backtest_results(strategy_name, rank_score DESC)",
                "CREATE INDEX IF NOT EXISTS idx_backtest_results_date ON backtest_results(backtest_date DESC)",
                "CREATE INDEX IF NOT EXISTS idx_backtest_results_sharpe ON backtest_results(sharpe_ratio DESC)",
                # Backtest trade indexes (updated for symbol_id FK)
                "CREATE INDEX IF NOT EXISTS idx_backtest_trades_result_id ON backtest_trades(backtest_result_id)",
                "CREATE INDEX IF NOT EXISTS idx_backtest_trades_backtest_id ON backtest_trades(backtest_backtest_id)",
                "CREATE INDEX IF NOT EXISTS idx_backtest_trades_symbol_id ON backtest_trades(symbol_id)",
                # Live trade indexes (updated for symbol_id FK)
                "CREATE INDEX IF NOT EXISTS idx_trades_symbol_status ON trades(symbol_id, status)",
                "CREATE INDEX IF NOT EXISTS idx_trades_open_time ON trades(open_time DESC)",
                "CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy_name)",
                # Optimal parameters indexes (updated for symbol_id FK)
                "CREATE INDEX IF NOT EXISTS idx_optimal_params_symbol_timeframe ON optimal_parameters(symbol_id, timeframe, strategy_name)",
                # Tradable pairs indexes
                "CREATE INDEX IF NOT EXISTS idx_tradable_pairs_symbol ON tradable_pairs(symbol)",
                "CREATE INDEX IF NOT EXISTS idx_tradable_pairs_id ON tradable_pairs(id)",
            ]

            for index_sql in indexes:
                cursor.execute(index_sql)

            self.conn.commit()
            self.logger.info("All database indexes created successfully")
            return True

        except sqlite3.Error as e:
            self.logger.error("Failed to create database indexes: %s", e)
            return False

    def fresh_init(self) -> bool:
        """Drop all tables and recreate fresh schema (used for init mode).

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()

            # Disable foreign keys to allow dropping tables with FK constraints
            cursor.execute("PRAGMA foreign_keys=OFF")

            # Drop all tables
            tables_to_drop = [
                "market_data",
                "backtest_market_data",
                "tradable_pairs",
                "optimal_parameters",
                "backtest_backtests",
                "backtest_results",
                "backtest_strategies",
                "backtest_trades",
                "trades",
            ]

            for table in tables_to_drop:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")

            self.conn.commit()
            self.logger.info("Dropped all tables for fresh initialization")

            # Re-enable foreign keys
            cursor.execute("PRAGMA foreign_keys=ON")

            # Recreate all tables and indexes
            if not self.create_tables():
                return False
            if not self.create_indexes():
                return False

            self.logger.info("Fresh database schema created successfully")
            return True

        except sqlite3.Error as e:
            self.logger.error("Failed to recreate fresh schema: %s", e)
            return False

    def migrate(self) -> bool:
        """Perform schema migrations with version tracking.

        Handles:
        - Merging backtest_market_data into market_data
        - Converting to composite primary key (time, symbol, timeframe)
        - Adding real_volume column if missing

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()

            # Check/create schema_version table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_version (version INTEGER)
            """
            )
            self.conn.commit()

            # Get current schema version
            try:
                cursor.execute("SELECT version FROM schema_version")
                result = cursor.fetchone()
                version = result[0] if result else 0
            except sqlite3.OperationalError:
                version = 0

            if version == 0:
                # Insert initial version if not exists
                cursor.execute("DELETE FROM schema_version")  # Clear any partial data
                cursor.execute("INSERT INTO schema_version VALUES (0)")
                self.conn.commit()
                version = 0

            # Migration to version 1: Merge backtest_market_data into market_data
            if version < 1:
                self.logger.info("Running migration to schema version 1...")

                # Step 1: Merge backtest_market_data if exists
                try:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO market_data 
                        (time, symbol, timeframe, open, high, low, close, tick_volume, spread, real_volume)
                        SELECT time, symbol, timeframe, open, high, low, close, tick_volume, spread, real_volume 
                        FROM backtest_market_data
                    """
                    )
                    self.conn.commit()
                    self.logger.info("Merged backtest_market_data into market_data")

                    # Drop old table
                    cursor.execute("DROP TABLE IF EXISTS backtest_market_data")
                    self.conn.commit()
                    self.logger.info("Dropped backtest_market_data table")
                except sqlite3.OperationalError as e:
                    self.logger.debug("backtest_market_data merge skipped: %s", e)

                # Step 2: Ensure market_data has composite primary key (time, symbol, timeframe)
                # Check if market_data already has the new schema
                cursor.execute("PRAGMA table_info(market_data)")
                columns = {row[1]: row[2] for row in cursor.fetchall()}

                if "symbol" not in columns or "id" in columns:
                    # Old schema detected - rename and recreate with new schema
                    self.logger.info(
                        "Converting market_data to new schema with composite key..."
                    )

                    cursor.execute("ALTER TABLE market_data RENAME TO market_data_old")
                    self.conn.commit()

                    # Create new market_data with composite primary key
                    cursor.execute(
                        """
                        CREATE TABLE market_data (
                            time TEXT NOT NULL,
                            symbol TEXT NOT NULL,
                            timeframe TEXT NOT NULL,
                            open REAL NOT NULL,
                            high REAL NOT NULL,
                            low REAL NOT NULL,
                            close REAL NOT NULL,
                            tick_volume INTEGER,
                            spread REAL,
                            real_volume INTEGER,
                            PRIMARY KEY (time, symbol, timeframe)
                        )
                    """
                    )
                    self.conn.commit()

                    # Migrate data from old table
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO market_data 
                        (time, symbol, timeframe, open, high, low, close, tick_volume, spread, real_volume)
                        SELECT 
                            time, 
                            COALESCE(symbol, (SELECT symbol FROM tradable_pairs WHERE id = symbol_id LIMIT 1)) as symbol,
                            timeframe,
                            open, high, low, close,
                            volume as tick_volume,
                            0 as spread,
                            0 as real_volume
                        FROM market_data_old
                    """
                    )
                    self.conn.commit()
                    self.logger.info("Migrated data to new market_data schema")

                    cursor.execute("DROP TABLE market_data_old")
                    self.conn.commit()

                # Update schema version to 1
                cursor.execute("UPDATE schema_version SET version = 1")
                self.conn.commit()
                self.logger.info("Schema migration to version 1 complete")

            self.logger.info("All migrations completed successfully")
            return True

        except sqlite3.Error as e:
            self.logger.error("Migration failed: %s", e)
            return False

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database.

        Args:
            table_name: Name of the table to check

        Returns:
            True if table exists, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            )
            return cursor.fetchone() is not None
        except sqlite3.Error as e:
            self.logger.error("Failed to check if table exists: %s", e)
            return False

    def migrate_tables(self) -> bool:
        """Run all required migrations to ensure schema is up-to-date.

        Handles two scenarios:
        - Fresh database: Creates all tables
        - Existing database: Detects schema version and migrates if needed

        Note: For full fresh initialization (testing/demo), use fresh_init() instead.
        This method preserves existing data and only updates schema if needed.

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]

            if table_count == 0:
                # Fresh database - create all tables
                self.logger.info("Fresh database detected - creating all tables")
                return self.create_tables() and self.create_indexes()

            # Existing database - check schema version by detecting symbol_id FK
            cursor.execute("PRAGMA table_info(market_data)")
            columns = [col[1] for col in cursor.fetchall()]
            has_symbol_id = "symbol_id" in columns  # Old schema indicator

            if not has_symbol_id:
                # Already v2 schema (direct symbol column, no symbol_id FK)
                self.logger.info("V2 schema detected - ensuring indexes and MT5 fields")
                # Ensure MT5 sync fields are present in trades table
                self._add_mt5_sync_fields_to_trades(cursor)
                return self.create_indexes()

            # Old schema with symbol_id FK detected - migrate to v2
            self.logger.info("Old schema detected - migrating to v2")
            try:
                cursor.execute("DROP TABLE IF EXISTS market_data")
                cursor.execute("DROP TABLE IF EXISTS backtest_market_data")
                cursor.execute("DROP TABLE IF EXISTS optimal_parameters")
                cursor.execute("DROP TABLE IF EXISTS trades")
                cursor.execute("DROP TABLE IF EXISTS backtest_trades")
                cursor.execute("DROP TABLE IF EXISTS tradable_pairs")
                self.conn.commit()
                self.logger.info("Dropped old schema tables")
            except sqlite3.Error as e:
                self.logger.warning("Error dropping old tables: %s", e)

            return self.create_tables() and self.create_indexes()

        except sqlite3.Error as e:
            self.logger.error("Migration failed: %s", e)
            return False

    def migrate_to_v2_schema(self) -> bool:
        """Migrate from old schema to v2 with proper FKs and JSON metrics.

        This migration:
        1. Reads data from old tables (market_data, optimal_parameters, backtest_results)
        2. Populates symbol_id by looking up symbols in tradable_pairs
        3. Stores metrics as JSON in backtest_backtests
        4. Creates backups of old tables

        Returns:
            True if migration successful, False otherwise
        """
        try:
            cursor = self.conn.cursor()

            self.logger.info("Starting schema migration to v2 with FKs")

            # Step 1: Migrate market_data
            self._migrate_market_data(cursor)

            # Step 2: Migrate backtest_market_data
            self._migrate_backtest_market_data(cursor)

            # Step 3: Migrate optimal_parameters
            self._migrate_optimal_parameters(cursor)

            # Step 4: Migrate backtest_results to backtest_backtests
            self._migrate_backtest_results(cursor)

            # Step 5: Migrate trades table
            self._migrate_trades(cursor)

            # Step 6: Add MT5 sync fields to trades table
            self._add_mt5_sync_fields_to_trades(cursor)

            # Step 7: Populate backtest_strategies if needed
            self._populate_backtest_strategies(cursor)

            self.conn.commit()
            self.logger.info("Schema migration to v2 completed successfully")
            return True

        except sqlite3.Error as e:
            self.conn.rollback()
            self.logger.error("Schema migration failed: %s", e)
            return False

    def _migrate_market_data(self, cursor) -> None:
        """Migrate market_data from symbol TEXT to symbol_id FK.

        Args:
            cursor: SQLite cursor object.

        Returns:
            None.
        """
        try:
            # Check if already migrated
            cursor.execute("PRAGMA table_info(market_data)")
            columns = [col[1] for col in cursor.fetchall()]

            if "symbol_id" in columns:
                self.logger.info("market_data already migrated")
                return

            self.logger.info("Migrating market_data table...")

            # Create temporary table with new schema
            cursor.execute(
                """
                CREATE TABLE market_data_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol_id INTEGER NOT NULL,
                    timeframe TEXT NOT NULL,
                    time TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    type TEXT DEFAULT 'live',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (symbol_id) REFERENCES tradable_pairs(id),
                    UNIQUE(symbol_id, timeframe, time)
                )
            """
            )

            # Migrate data with symbol_id lookup
            cursor.execute(
                """
                INSERT INTO market_data_v2 
                (symbol_id, timeframe, time, open, high, low, close, volume, type, created_at)
                SELECT tp.id, md.timeframe, md.time, md.open, md.high, md.low, md.close, 
                       COALESCE(md.tick_volume, md.real_volume, 0), 'live', CURRENT_TIMESTAMP
                FROM market_data md
                LEFT JOIN tradable_pairs tp ON md.symbol = tp.symbol
            """
            )

            # Swap tables
            cursor.execute("DROP TABLE market_data")
            cursor.execute("ALTER TABLE market_data_v2 RENAME TO market_data")

            self.logger.info("Migrated market_data with symbol_id FK")

        except sqlite3.Error as e:
            self.logger.warning("Could not migrate market_data: %s", e)

    def _migrate_backtest_market_data(self, cursor) -> None:
        """Migrate backtest_market_data from symbol TEXT to symbol_id FK.

        Args:
            cursor: SQLite cursor object.

        Returns:
            None.
        """
        try:
            cursor.execute("PRAGMA table_info(backtest_market_data)")
            columns = [col[1] for col in cursor.fetchall()]

            if "symbol_id" in columns:
                self.logger.info("backtest_market_data already migrated")
                return

            self.logger.info("Migrating backtest_market_data table...")

            cursor.execute(
                """
                CREATE TABLE backtest_market_data_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol_id INTEGER NOT NULL,
                    timeframe TEXT NOT NULL,
                    time TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (symbol_id) REFERENCES tradable_pairs(id),
                    UNIQUE(symbol_id, timeframe, time)
                )
            """
            )

            cursor.execute(
                """
                INSERT INTO backtest_market_data_v2 
                (symbol_id, timeframe, time, open, high, low, close, volume, created_at)
                SELECT tp.id, bmd.timeframe, bmd.time, bmd.open, bmd.high, bmd.low, bmd.close, 
                       COALESCE(bmd.tick_volume, bmd.real_volume, 0), CURRENT_TIMESTAMP
                FROM backtest_market_data bmd
                LEFT JOIN tradable_pairs tp ON bmd.symbol = tp.symbol
            """
            )

            cursor.execute("DROP TABLE backtest_market_data")
            cursor.execute(
                "ALTER TABLE backtest_market_data_v2 RENAME TO backtest_market_data"
            )

            self.logger.info("Migrated backtest_market_data with symbol_id FK")

        except sqlite3.Error as e:
            self.logger.warning("Could not migrate backtest_market_data: %s", e)

    def _migrate_optimal_parameters(self, cursor) -> None:
        """Migrate optimal_parameters from symbol TEXT to symbol_id FK.

        Args:
            cursor: SQLite cursor object.

        Returns:
            None.
        """
        try:
            cursor.execute("PRAGMA table_info(optimal_parameters)")
            columns = [col[1] for col in cursor.fetchall()]

            if "symbol_id" in columns:
                self.logger.info("optimal_parameters already migrated")
                return

            self.logger.info("Migrating optimal_parameters table...")

            cursor.execute(
                """
                CREATE TABLE optimal_parameters_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol_id INTEGER NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    parameter_value TEXT NOT NULL,
                    metrics TEXT,
                    last_optimized TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (symbol_id) REFERENCES tradable_pairs(id),
                    UNIQUE(symbol_id, timeframe, strategy_name)
                )
            """
            )

            cursor.execute(
                """
                INSERT INTO optimal_parameters_v2 
                (symbol_id, timeframe, strategy_name, parameter_value, metrics, last_optimized)
                SELECT tp.id, op.timeframe, op.strategy_name, op.parameter_value, op.metrics, op.last_optimized
                FROM optimal_parameters op
                LEFT JOIN tradable_pairs tp ON op.symbol = tp.symbol
            """
            )

            cursor.execute("DROP TABLE optimal_parameters")
            cursor.execute(
                "ALTER TABLE optimal_parameters_v2 RENAME TO optimal_parameters"
            )

            self.logger.info("Migrated optimal_parameters with symbol_id FK")

        except sqlite3.Error as e:
            self.logger.warning("Could not migrate optimal_parameters: %s", e)

    def _migrate_backtest_results(self, cursor) -> None:
        """Migrate backtest_results to backtest_backtests with JSON metrics.

        Args:
            cursor: SQLite cursor object.

        Returns:
            None.
        """
        try:
            # Check if backtest_backtests already has data
            cursor.execute("SELECT COUNT(*) FROM backtest_backtests")
            count = cursor.fetchone()[0]

            if count > 0:
                self.logger.info("backtest_backtests already populated")
                return

            self.logger.info("Migrating backtest_results to backtest_backtests...")

            # Check if backtest_results exists
            cursor.execute(
                """
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='table' AND name='backtest_results'
            """
            )
            if cursor.fetchone()[0] == 0:
                self.logger.info("No backtest_results table to migrate")
                return

            # Migrate with JSON metrics
            cursor.execute(
                """
                INSERT INTO backtest_backtests 
                (strategy_id, symbol_id, timeframe, metrics, timestamp)
                SELECT 
                    COALESCE(bs.id, 1),
                    COALESCE(tp.id, 1),
                    br.timeframe,
                    json_object(
                        'sharpe_ratio', br.sharpe_ratio,
                        'total_return', COALESCE(br.return_pct, 0),
                        'win_rate', COALESCE(br.win_rate_pct / 100.0, 0),
                        'profit_factor', br.profit_factor,
                        'max_drawdown', COALESCE(br.max_drawdown_pct / 100.0, 0),
                        'rank_score', COALESCE(br.rank_score, 0)
                    ),
                    datetime(br.backtest_date)
                FROM backtest_results br
                LEFT JOIN backtest_strategies bs ON br.strategy_name = bs.name
                LEFT JOIN tradable_pairs tp ON br.symbol = tp.symbol
                ON CONFLICT(strategy_id, symbol_id, timeframe) DO NOTHING
            """
            )

            self.logger.info("Migrated backtest_results to backtest_backtests")

        except sqlite3.Error as e:
            self.logger.warning("Could not migrate backtest_results: %s", e)

    def _migrate_trades(self, cursor) -> None:
        """Migrate trades from symbol TEXT to symbol_id FK.

        Args:
            cursor: SQLite cursor object.

        Returns:
            None.
        """
        try:
            cursor.execute("PRAGMA table_info(trades)")
            columns = [col[1] for col in cursor.fetchall()]

            if "symbol_id" in columns:
                self.logger.info("trades already migrated")
                return

            self.logger.info("Migrating trades table...")

            cursor.execute(
                """
                CREATE TABLE trades_v2 (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol_id INTEGER NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    trade_type TEXT NOT NULL,
                    volume REAL NOT NULL,
                    open_price REAL NOT NULL,
                    close_price REAL,
                    open_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    close_time TIMESTAMP,
                    profit REAL,
                    status TEXT DEFAULT 'open',
                    order_id INTEGER,
                    deal_id INTEGER,
                    ticket INTEGER,
                    magic INTEGER,
                    swap REAL DEFAULT 0,
                    commission REAL DEFAULT 0,
                    comment TEXT,
                    external BOOLEAN DEFAULT 0,
                    mt5_synced_at TIMESTAMP,
                    FOREIGN KEY (symbol_id) REFERENCES tradable_pairs(id)
                )
            """
            )

            cursor.execute(
                """
                INSERT INTO trades_v2 
                (symbol_id, timeframe, strategy_name, trade_type, volume, open_price, 
                 close_price, open_time, close_time, profit, status, order_id, deal_id)
                SELECT COALESCE(tp.id, 1), t.timeframe, t.strategy_name, t.trade_type, t.volume, 
                       t.open_price, t.close_price, t.open_time, t.close_time, t.profit, 
                       t.status, t.order_id, t.deal_id
                FROM trades t
                LEFT JOIN tradable_pairs tp ON t.symbol = tp.symbol
                WHERE tp.id IS NOT NULL
            """
            )

            cursor.execute("DROP TABLE trades")
            cursor.execute("ALTER TABLE trades_v2 RENAME TO trades")

            self.logger.info("Migrated trades with symbol_id FK")

        except sqlite3.Error as e:
            self.logger.warning("Could not migrate trades: %s", e)

    def _add_mt5_sync_fields_to_trades(self, cursor) -> None:
        """Add MT5 synchronization fields to trades table.
        
        Adds: ticket, magic, swap, commission, comment, external, mt5_synced_at
        
        Args:
            cursor: SQLite cursor object.
            
        Returns:
            None.
        """
        try:
            cursor.execute("PRAGMA table_info(trades)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Check if MT5 sync fields already exist
            if "ticket" in columns and "mt5_synced_at" in columns:
                self.logger.info("MT5 sync fields already exist in trades table")
                return
            
            self.logger.info("Adding MT5 sync fields to trades table...")
            
            # Add new columns one by one
            new_columns = [
                ("ticket", "INTEGER"),
                ("magic", "INTEGER"),
                ("swap", "REAL DEFAULT 0"),
                ("commission", "REAL DEFAULT 0"),
                ("comment", "TEXT"),
                ("external", "BOOLEAN DEFAULT 0"),
                ("mt5_synced_at", "TIMESTAMP"),
            ]
            
            for col_name, col_type in new_columns:
                if col_name not in columns:
                    try:
                        cursor.execute(f"ALTER TABLE trades ADD COLUMN {col_name} {col_type}")
                        self.logger.info(f"Added column {col_name} to trades table")
                    except sqlite3.Error as e:
                        self.logger.debug(f"Column {col_name} may already exist: {e}")
            
            self.conn.commit()
            self.logger.info("MT5 sync fields added successfully")
            
        except sqlite3.Error as e:
            self.logger.warning("Could not add MT5 sync fields to trades: %s", e)

    def _populate_backtest_strategies(self, cursor) -> None:
        """Populate backtest_strategies table from backtest_results.

        Args:
            cursor: SQLite cursor object.

        Returns:
            None.
        """
        try:
            cursor.execute("SELECT COUNT(*) FROM backtest_strategies")
            count = cursor.fetchone()[0]

            if count > 0:
                self.logger.info("backtest_strategies already populated")
                return

            cursor.execute(
                """
                SELECT COUNT(*) FROM sqlite_master 
                WHERE type='table' AND name='backtest_results'
            """
            )
            if cursor.fetchone()[0] == 0:
                self.logger.info("No backtest_results table to populate from")
                return

            self.logger.info("Populating backtest_strategies...")

            cursor.execute(
                """
                INSERT OR IGNORE INTO backtest_strategies (name)
                SELECT DISTINCT strategy_name FROM backtest_results
                WHERE strategy_name IS NOT NULL
            """
            )

            self.logger.info("Populated backtest_strategies")

        except sqlite3.Error as e:
            self.logger.warning("Could not populate backtest_strategies: %s", e)
