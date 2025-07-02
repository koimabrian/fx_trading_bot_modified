# src/database/db_manager.py
import sqlite3
import pandas as pd
import logging
import yaml
from abc import ABC, abstractmethod

from src.utils.logger import setup_logging

setup_logging()

class DatabaseConfig:
    """Global configuration for database settings."""
    TABLE_PREFIX = 'backtest_'
    PARAMS_TABLE = 'optimal_params'

class SchemaManager:
    """Manages database schema and migrations."""
    def __init__(self, conn, config):
        self.conn = conn
        self.config = config
        self.logger = logging.getLogger(__name__)

    def create_tables(self):
        """Create necessary database tables."""
        tables = {
            f"{self.config.get('backtesting', {}).get('database', {}).get('table_prefix', DatabaseConfig.TABLE_PREFIX)}market_data": """
                CREATE TABLE IF NOT EXISTS {table} (
                    time TEXT,
                    symbol TEXT,
                    timeframe TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    tick_volume INTEGER,
                    spread REAL,
                    real_volume INTEGER,
                    PRIMARY KEY (time, symbol, timeframe)
                )
            """,
            f"{self.config.get('backtesting', {}).get('database', {}).get('table_prefix', DatabaseConfig.TABLE_PREFIX)}strategies": """
                CREATE TABLE IF NOT EXISTS {table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    parameters TEXT,
                    filters TEXT,
                    score REAL,
                    status TEXT,
                    is_ml BOOLEAN
                )
            """,
            f"{self.config.get('backtesting', {}).get('database', {}).get('table_prefix', DatabaseConfig.TABLE_PREFIX)}backtests": """
                CREATE TABLE IF NOT EXISTS {table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id INTEGER,
                    metrics TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (strategy_id) REFERENCES {prefix}strategies(id)
                )
            """,
            f"{self.config.get('backtesting', {}).get('database', {}).get('table_prefix', '')}{DatabaseConfig.PARAMS_TABLE}": """
                CREATE TABLE IF NOT EXISTS {table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT,
                    timeframe TEXT,
                    strategy_name TEXT,
                    period INTEGER,
                    volatility_factor REAL,
                    lot_size REAL,
                    buy_threshold INTEGER,
                    sell_threshold INTEGER,
                    sharpe_ratio REAL,
                    timestamp TEXT
                )
            """,
            "strategies": """
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
        }
        try:
            cursor = self.conn.cursor()
            for table_name, create_stmt in tables.items():
                cursor.execute(create_stmt.format(table=table_name, prefix=self.config.get('backtesting', {}).get('database', {}).get('table_prefix', DatabaseConfig.TABLE_PREFIX)))
            self.conn.commit()
            self.logger.info("Database tables created successfully")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to create tables: {e}")
            raise

    def migrate(self):
        """Perform database migrations and cleanup."""
        try:
            cursor = self.conn.cursor()
            tables = ['market_data', 'strategies', 'backtests', DatabaseConfig.PARAMS_TABLE]
            prefix = self.config.get('backtesting', {}).get('database', {}).get('table_prefix', DatabaseConfig.TABLE_PREFIX)
            for table in tables:
                table_name = f"{prefix}{table}" if table != 'strategies' or prefix else table
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                self.logger.info(f"Dropped table: {table_name}")
            self.conn.commit()
            self.create_tables()
            self.logger.info("Database migration completed successfully")
        except sqlite3.Error as e:
            self.logger.error(f"Failed to migrate database: {e}")
            raise

class AbstractDatabaseManager(ABC):
    """Abstract base class for database management."""
    @abstractmethod
    def connect(self):
        pass

    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def execute_query(self, query, params=None):
        pass

class DatabaseManager(AbstractDatabaseManager):
    """Manages database connections and operations."""
    _instance = None

    def __new__(cls, config):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, config):
        if not hasattr(self, 'initialized'):
            self.config = config
            self.conn = None
            self.schema_manager = None
            self.logger = logging.getLogger(__name__)
            self.initialized = True

    def connect(self):
        """Establish database connection."""
        if self.conn is None:
            try:
                self.conn = sqlite3.connect(self.config.get('path', 'src/data/market_data.sqlite'))
                self.schema_manager = SchemaManager(self.conn, self.config)
                self.schema_manager.create_tables()
                self.logger.info("Database connection established")
            except sqlite3.Error as e:
                self.logger.error(f"Failed to connect to database: {e}")
                raise

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.logger.info("Database connection closed")

    def execute_query(self, query, params=None):
        """Execute a SQL query with optional parameters."""
        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.conn.commit()
            return cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Query execution failed: {query}, Error: {e}")
            raise

    def get_optimized_params(self, symbol, timeframe, strategy_name):
        """Retrieve optimized parameters from the database."""
        table = f"{self.config.get('backtesting', {}).get('database', {}).get('table_prefix', '')}{DatabaseConfig.PARAMS_TABLE}"
        query = f"SELECT * FROM {table} WHERE symbol = ? AND timeframe = ? AND strategy_name = ? ORDER BY timestamp DESC LIMIT 1"
        result = self.execute_query(query, (symbol, timeframe, strategy_name))
        return result[0] if result else None