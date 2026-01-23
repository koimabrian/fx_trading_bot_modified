# fx_trading_bot/src/database/db_manager.py
# Purpose: Manages database connections and operations
import logging
import os
import sqlite3
from abc import ABC, abstractmethod

from src.utils.logger import setup_logging

setup_logging()


class DatabaseConfig:
    """Global configuration for database settings."""

    TABLE_PREFIX = "backtest_"
    PARAMS_TABLE = "optimal_params"


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

    @abstractmethod
    def create_tables(self):
        pass


class DatabaseManager(AbstractDatabaseManager):
    """Manages database connections and operations."""

    def __init__(self, config):
        """Initialize DatabaseManager.

        Args:
            config: Configuration dictionary with database settings
        """
        self.config = config
        self.conn = None
        self.logger = logging.getLogger(__name__)

    def __enter__(self):
        """Context manager entry point."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point."""
        self.close()

    def connect(self):
        """Establish database connection and ensure data directory exists."""
        try:
            db_path = self.config.get("path", "src/data/market_data.sqlite")
            # Auto-create src/data directory if it doesn't exist
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            self.conn = sqlite3.connect(db_path)
            # Set row_factory to return dicts instead of tuples for easier access
            self.conn.row_factory = sqlite3.Row
            self.logger.info("Database connection established")
        except sqlite3.Error as e:
            self.logger.error("Failed to connect to database: %s", e)
            raise

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.logger.info("Database connection closed")

    def execute_query(self, query, params=None):
        """Execute a SQL query with optional parameters.

        Args:
            query: SQL query string
            params: Optional parameters for parameterized query

        Returns:
            Cursor object with query results
        """
        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.conn.commit()
            return cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error("Query execution failed: %s, Error: %s", query, e)
            raise

    def create_indexes(self):
        """Create indexes on frequently queried columns for performance."""
        try:
            cursor = self.conn.cursor()
            # Check which tables exist before creating indexes
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = set(row[0] for row in cursor.fetchall())

            indexes = [
                (
                    "market_data",
                    "CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timeframe ON market_data(symbol, timeframe, time DESC)",
                ),
                (
                    "market_data",
                    "CREATE INDEX IF NOT EXISTS idx_market_data_time ON market_data(time DESC)",
                ),
                (
                    "backtest_market_data",
                    "CREATE INDEX IF NOT EXISTS idx_backtest_market_data_symbol_timeframe ON backtest_market_data(symbol, timeframe, time DESC)",
                ),
                (
                    "trades",
                    "CREATE INDEX IF NOT EXISTS idx_trades_strategy_id ON trades(strategy_id)",
                ),
                (
                    "trades",
                    "CREATE INDEX IF NOT EXISTS idx_trades_pair ON trades(pair)",
                ),
            ]

            for table_name, index_sql in indexes:
                # Only create index if the table exists
                if table_name in existing_tables:
                    cursor.execute(index_sql)

            self.conn.commit()
            self.logger.info("Database indexes created successfully")
        except sqlite3.Error as e:
            self.logger.error("Failed to create indexes: %s", e)

    def create_tables(self):
        """Create necessary database tables based on config."""
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
                    name TEXT UNIQUE
                )
            """,
            f"{self.config.get('backtesting', {}).get('database', {}).get('table_prefix', DatabaseConfig.TABLE_PREFIX)}backtests": """
                CREATE TABLE IF NOT EXISTS {table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id INTEGER,
                    symbol TEXT,
                    timeframe TEXT,
                    metrics TEXT,
                    timestamp TEXT,
                    UNIQUE(strategy_id, symbol, timeframe),
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
            "trades": """
                CREATE TABLE IF NOT EXISTS {table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id INTEGER,
                    pair TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    volume REAL,
                    timestamp TEXT,
                    exit_timestamp TEXT,
                    profit REAL,
                    mode TEXT,
                    order_id INTEGER,
                    deal_id INTEGER,
                    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
                )
            """,
            "strategies": """
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
        }
        try:
            cursor = self.conn.cursor()
            for table_name, create_stmt in tables.items():
                cursor.execute(
                    create_stmt.format(
                        table=table_name,
                        prefix=self.config.get("backtesting", {})
                        .get("database", {})
                        .get("table_prefix", DatabaseConfig.TABLE_PREFIX),
                    )
                )
            self.conn.commit()
            self.logger.info("Database tables and indexes created successfully")
        except sqlite3.Error as e:
            self.logger.error("Failed to create tables: %s", e)
            raise

    def get_optimized_params(self, symbol, timeframe, strategy_name):
        """Retrieve optimized parameters from the database."""
        table = f"{self.config.get('backtesting', {}).get('database', {}).get('table_prefix', '')}{DatabaseConfig.PARAMS_TABLE}"
        query = f"SELECT * FROM {table} WHERE symbol = ? AND timeframe = ? AND strategy_name = ? ORDER BY timestamp DESC LIMIT 1"
        result = self.execute_query(query, (symbol, timeframe, strategy_name))
        return result[0] if result else None

    def create_backtest_tables(self):
        """Create tables for backtest results storage."""
        try:
            cursor = self.conn.cursor()

            # Table 1: backtest_results (enhanced with trade statistics and rank score)
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
                    created_at TEXT NOT NULL,
                    UNIQUE(symbol, strategy_name, timeframe, start_date, end_date, backtest_date)
                )
            """
            )

            # Table 2: backtest_trades
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS backtest_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backtest_result_id INTEGER,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    volume REAL NOT NULL,
                    profit REAL NOT NULL,
                    profit_pct REAL NOT NULL,
                    duration_hours REAL,
                    FOREIGN KEY (backtest_result_id) REFERENCES backtest_results(id)
                )
            """
            )

            # Table 3: rolling_metrics
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS rolling_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backtest_result_id INTEGER,
                    date TEXT NOT NULL,
                    rolling_6m_profit_pct REAL,
                    rolling_12m_profit_pct REAL,
                    rolling_18m_profit_pct REAL,
                    cumulative_profit_pct REAL,
                    drawdown_pct REAL,
                    UNIQUE(backtest_result_id, date),
                    FOREIGN KEY (backtest_result_id) REFERENCES backtest_results(id)
                )
            """
            )

            # Create indexes for backtest tables (critical for query performance)
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_backtest_results_symbol_timeframe ON backtest_results(symbol, timeframe, rank_score DESC)",
                "CREATE INDEX IF NOT EXISTS idx_backtest_results_strategy_rank ON backtest_results(strategy_name, rank_score DESC)",
                "CREATE INDEX IF NOT EXISTS idx_backtest_results_date ON backtest_results(backtest_date DESC)",
                "CREATE INDEX IF NOT EXISTS idx_backtest_results_sharpe ON backtest_results(sharpe_ratio DESC)",
                "CREATE INDEX IF NOT EXISTS idx_backtest_trades_result_id ON backtest_trades(backtest_result_id)",
                "CREATE INDEX IF NOT EXISTS idx_rolling_metrics_result_id ON rolling_metrics(backtest_result_id)",
            ]

            for index_sql in indexes:
                cursor.execute(index_sql)

            self.conn.commit()
            self.logger.info("Backtest tables and indexes created successfully")
        except sqlite3.Error as e:
            self.logger.error("Failed to create backtest tables: %s", e)
            raise

    def save_backtest_results(self, results_dict):
        """Save backtest results to database with comprehensive metrics.

        Args:
            results_dict: Dictionary with backtest results including:
                - symbol, strategy_name, timeframe
                - start_date, end_date, backtest_date
                - metrics: sharpe_ratio, return_pct, max_drawdown_pct, profit_factor,
                          total_trades, winning_trades, losing_trades, win_rate_pct,
                          avg_win, avg_loss, pl_ratio, recovery_factor, sortino_ratio,
                          calmar_ratio
                - trades: list of individual trade results

        Returns:
            backtest_result_id if successful, None otherwise
        """
        try:
            from src.core.strategy_selector import StrategySelector

            metrics = results_dict.get("metrics", {})
            trades = results_dict.get("trades", [])

            # Compute rank score using StrategySelector
            selector = StrategySelector(self)
            rank_score = selector.compute_rank_score(
                sharpe_ratio=metrics.get("sharpe_ratio", 0),
                return_pct=metrics.get("return_pct", 0),
                win_rate_pct=metrics.get("win_rate_pct", 50),
                profit_factor=metrics.get("profit_factor", 1),
            )

            cursor = self.conn.cursor()

            # Insert backtest_results with all metrics including rank_score
            cursor.execute(
                """
                INSERT OR REPLACE INTO backtest_results (
                    symbol, strategy_name, timeframe, start_date, end_date, backtest_date,
                    created_at, total_profit_pct, return_pct, sharpe_ratio, sortino_ratio,
                    calmar_ratio, max_drawdown_pct, profit_factor, total_trades,
                    winning_trades, losing_trades, win_rate_pct, avg_win, avg_loss,
                    pl_ratio, recovery_factor, rank_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    results_dict["symbol"],
                    results_dict["strategy_name"],
                    results_dict["timeframe"],
                    results_dict["start_date"],
                    results_dict["end_date"],
                    results_dict.get("backtest_date", results_dict.get("created_at")),
                    results_dict["created_at"],
                    metrics.get("total_profit_pct"),
                    metrics.get("return_pct"),
                    metrics.get("sharpe_ratio"),
                    metrics.get("sortino_ratio"),
                    metrics.get("calmar_ratio"),
                    metrics.get("max_drawdown_pct"),
                    metrics.get("profit_factor"),
                    metrics.get("total_trades", 0),
                    metrics.get("winning_trades", 0),
                    metrics.get("losing_trades", 0),
                    metrics.get("win_rate_pct", 0),
                    metrics.get("avg_win"),
                    metrics.get("avg_loss"),
                    metrics.get("pl_ratio"),
                    metrics.get("recovery_factor"),
                    rank_score,
                ),
            )

            backtest_result_id = cursor.lastrowid

            # Insert backtest_trades if provided
            if trades:
                for trade in trades:
                    cursor.execute(
                        """
                        INSERT INTO backtest_trades (
                            backtest_result_id, entry_time, exit_time, symbol,
                            entry_price, exit_price, volume, profit, profit_pct, duration_hours
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            backtest_result_id,
                            (
                                trade["entry_time"].isoformat()
                                if hasattr(trade["entry_time"], "isoformat")
                                else trade["entry_time"]
                            ),
                            (
                                trade["exit_time"].isoformat()
                                if hasattr(trade["exit_time"], "isoformat")
                                else trade["exit_time"]
                            ),
                            trade["symbol"],
                            trade["entry_price"],
                            trade["exit_price"],
                            trade["volume"],
                            trade["profit"],
                            trade["profit_pct"],
                            trade.get("duration_hours"),
                        ),
                    )

            self.conn.commit()
            self.logger.info(
                "Saved backtest results: %s (%s %s) - ID: %d, Trades: %d, Rank Score: %.2f",
                results_dict["strategy_name"],
                results_dict["symbol"],
                results_dict["timeframe"],
                backtest_result_id,
                len(trades),
                rank_score,
            )
            return backtest_result_id

        except sqlite3.Error as e:
            self.logger.error("Failed to save backtest results: %s", e)
            return None
