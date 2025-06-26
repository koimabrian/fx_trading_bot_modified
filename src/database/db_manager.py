# fx_trading_bot/src/database/db_manager.py
# Purpose: Manage database connections and schema
import sqlite3
import logging
import os

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.logger = logging.getLogger(__name__)

    def connect(self):
        """Establish database connection"""
        try:
            if not os.path.exists(os.path.dirname(self.db_path)):
                self.logger.error(f"Database directory does not exist: {os.path.dirname(self.db_path)}")
                raise FileNotFoundError(f"Database directory does not exist: {os.path.dirname(self.db_path)}")
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.logger.info("Database connection established")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to connect to database at {self.db_path}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error while connecting to database at {self.db_path}: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")

    def execute_query(self, query, params=()):
        """Execute a database query"""
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            self.conn.commit()
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            self.logger.error(f"Query execution failed: {query}, Error: {e}")
            raise

    def create_tables(self):
        """Create necessary database tables and indexes"""
        create_market_data_table = """
        CREATE TABLE IF NOT EXISTS market_data (
            time TEXT,  -- Changed from INTEGER to TEXT to store datetime strings
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            tick_volume INTEGER,
            spread INTEGER,
            real_volume INTEGER,
            symbol TEXT,
            timeframe TEXT
        )
        """
        create_strategies_table = """
        CREATE TABLE IF NOT EXISTS strategies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            parameters TEXT,
            filters TEXT,
            score REAL,
            status TEXT,
            is_ml BOOLEAN
        )
        """
        create_trades_table = """
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER,
            pair TEXT,
            entry_price REAL,
            volume REAL,
            timestamp TEXT,
            mode TEXT,
            order_id INTEGER,
            deal_id INTEGER,
            exit_price REAL,
            exit_timestamp TEXT,
            profit REAL
        )
        """
        create_backtests_table = """
        CREATE TABLE IF NOT EXISTS backtests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            strategy_id INTEGER,
            metrics TEXT,
            filter_variation TEXT,
            timestamp TEXT
        )
        """
        create_index_symbol = """
        CREATE INDEX IF NOT EXISTS idx_market_data_symbol ON market_data (symbol)
        """
        create_index_timeframe = """
        CREATE INDEX IF NOT EXISTS idx_market_data_timeframe ON market_data (timeframe)
        """
        try:
            # Check if the market_data table exists and migrate if necessary
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='market_data'")
            if cursor.fetchone():
                # Check the type of the time column
                cursor.execute("PRAGMA table_info(market_data)")
                columns = cursor.fetchall()
                time_column_type = next(col['type'] for col in columns if col['name'] == 'time')
                if time_column_type != 'TEXT':
                    # Migrate the table
                    self.logger.info("Migrating market_data table to change time column type to TEXT")
                    cursor.execute("ALTER TABLE market_data RENAME TO market_data_old")
                    self.execute_query(create_market_data_table)
                    # Convert Unix timestamps to datetime strings
                    cursor.execute("SELECT * FROM market_data_old")
                    old_data = cursor.fetchall()
                    for row in old_data:
                        row_dict = dict(row)
                        try:
                            # Try to convert the time value assuming it's a Unix timestamp
                            time_value = pd.to_datetime(int(row_dict['time']), unit='s').strftime('%Y-%m-%d %H:%M:%S')
                        except (ValueError, TypeError):
                            # If it's already a datetime string, use it as is
                            time_value = row_dict['time']
                        self.execute_query(
                            """
                            INSERT INTO market_data (time, open, high, low, close, tick_volume, spread, real_volume, symbol, timeframe)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (time_value, row_dict['open'], row_dict['high'], row_dict['low'], row_dict['close'],
                             row_dict['tick_volume'], row_dict['spread'], row_dict['real_volume'],
                             row_dict['symbol'], row_dict['timeframe'])
                        )
                    cursor.execute("DROP TABLE market_data_old")
                    self.logger.info("Migration of market_data table completed successfully")
            else:
                self.execute_query(create_market_data_table)

            self.execute_query(create_strategies_table)
            self.execute_query(create_trades_table)
            self.execute_query(create_backtests_table)
            self.execute_query(create_index_symbol)
            self.execute_query(create_index_timeframe)
            self.logger.info("Database tables and indexes created successfully")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to create tables or indexes: {e}")
            raise