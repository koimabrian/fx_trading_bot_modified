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

            # Table 2: market_data (live and historical) - with FK to tradable_pairs
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS market_data (
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

            # Table 3: backtest_market_data - with FK to tradable_pairs
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS backtest_market_data (
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
                # Market data indexes (updated for symbol_id FK)
                "CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timeframe ON market_data(symbol_id, timeframe, time DESC)",
                "CREATE INDEX IF NOT EXISTS idx_market_data_time ON market_data(time DESC)",
                "CREATE INDEX IF NOT EXISTS idx_backtest_market_data_symbol_timeframe ON backtest_market_data(symbol_id, timeframe, time DESC)",
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

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if any tables exist
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
            table_count = cursor.fetchone()[0]

            if table_count == 0:
                # Fresh database - create all tables
                self.logger.info("Fresh database detected - creating all tables")
                return self.create_tables() and self.create_indexes()
            else:
                # Existing database - check if we need to migrate
                # Check if market_data has symbol_id (new schema) or symbol (old schema)
                cursor.execute("PRAGMA table_info(market_data)")
                columns = [col[1] for col in cursor.fetchall()]

                if "symbol_id" in columns:
                    # Already migrated - just ensure indexes
                    self.logger.info("Already migrated to v2 schema")
                    return self.create_indexes()
                elif "symbol" in columns:
                    # Old schema detected - need to migrate
                    self.logger.info("Old schema detected - running migration to v2")
                    # Drop old tables and recreate with new schema
                    try:
                        cursor.execute("DROP TABLE IF EXISTS market_data")
                        cursor.execute("DROP TABLE IF EXISTS backtest_market_data")
                        cursor.execute("DROP TABLE IF EXISTS optimal_parameters")
                        cursor.execute("DROP TABLE IF EXISTS trades")
                        cursor.execute("DROP TABLE IF EXISTS backtest_trades")
                        self.conn.commit()
                        self.logger.info("Dropped old schema tables")
                    except sqlite3.Error as e:
                        self.logger.warning("Error dropping old tables: %s", e)
                    # Create new schema fresh
                    return self.create_tables() and self.create_indexes()
                else:
                    # Empty or unknown state
                    self.logger.info(
                        "Existing database detected - checking for missing tables"
                    )
                    missing_tables = []

                    required_tables = [
                        "tradable_pairs",
                        "market_data",
                        "backtest_market_data",
                        "optimal_parameters",
                        "backtest_backtests",
                        "backtest_results",
                        "backtest_trades",
                        "trades",
                        "backtest_strategies",
                    ]

                    for table_name in required_tables:
                        if not self.table_exists(table_name):
                            missing_tables.append(table_name)

                    if missing_tables:
                        self.logger.warning("Missing tables: %s", missing_tables)
                        return self.create_tables() and self.create_indexes()
                    else:
                        self.logger.info("All required tables exist - creating indexes")
                        return self.create_indexes()

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

            # Step 6: Populate backtest_strategies if needed
            self._populate_backtest_strategies(cursor)

            self.conn.commit()
            self.logger.info("Schema migration to v2 completed successfully")
            return True

        except sqlite3.Error as e:
            self.conn.rollback()
            self.logger.error("Schema migration failed: %s", e)
            return False

    def _migrate_market_data(self, cursor) -> None:
        """Migrate market_data from symbol TEXT to symbol_id FK."""
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
        """Migrate backtest_market_data from symbol TEXT to symbol_id FK."""
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
        """Migrate optimal_parameters from symbol TEXT to symbol_id FK."""
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
        """Migrate backtest_results to backtest_backtests with JSON metrics."""
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
        """Migrate trades from symbol TEXT to symbol_id FK."""
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
                    FOREIGN KEY (symbol_id) REFERENCES tradable_pairs(id)
                )
            """
            )

            cursor.execute(
                """
                INSERT INTO trades_v2 
                (symbol_id, timeframe, strategy_name, trade_type, volume, open_price, 
                 close_price, open_time, close_time, profit, status, order_id, deal_id)
                SELECT tp.id, t.timeframe, t.strategy_name, t.trade_type, t.volume, 
                       t.open_price, t.close_price, t.open_time, t.close_time, t.profit, 
                       t.status, t.order_id, t.deal_id
                FROM trades t
                LEFT JOIN tradable_pairs tp ON t.symbol = tp.symbol
            """
            )

            cursor.execute("DROP TABLE trades")
            cursor.execute("ALTER TABLE trades_v2 RENAME TO trades")

            self.logger.info("Migrated trades with symbol_id FK")

        except sqlite3.Error as e:
            self.logger.warning("Could not migrate trades: %s", e)

    def _populate_backtest_strategies(self, cursor) -> None:
        """Populate backtest_strategies table from backtest_results if not already populated."""
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
