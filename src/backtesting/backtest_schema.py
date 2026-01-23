# src/backtesting/backtest_schema.py
# Purpose: Database schema for backtest results storage

"""
Database schema additions for backtesting results and metrics.

This module defines the 3 new tables needed for comprehensive backtest result tracking:
1. backtest_results - Summary metrics per backtest run
2. backtest_trades - Detailed trade-by-trade data
3. rolling_metrics - Time-series rolling metrics (6m, 12m, 18m)
"""

# ============================================================================
# TABLE 1: backtest_results
# ============================================================================
import sqlite3


CREATE_BACKTEST_RESULTS_TABLE = """
    CREATE TABLE IF NOT EXISTS backtest_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        
        -- Metadata
        symbol TEXT NOT NULL,
        strategy_name TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        created_at TEXT NOT NULL,
        
        -- Core Metrics (5)
        total_profit_pct REAL,
        sharpe_ratio REAL,
        annual_return_pct REAL,
        max_drawdown_pct REAL,
        profit_factor REAL,
        
        -- Trade Statistics (4)
        total_orders INTEGER,
        win_rate_pct REAL,
        pl_ratio REAL,
        winner_avg_pct REAL,
        
        -- Additional Trade Stats
        loser_avg_pct REAL,
        
        -- Bonus Metrics (3)
        sortino_ratio REAL,
        calmar_ratio REAL,
        recovery_factor REAL,
        
        -- Additional Statistics
        total_profit REAL,
        total_loss REAL,
        largest_win REAL,
        largest_loss REAL,
        avg_trade_duration_hours REAL,
        
        -- Risk Metrics
        best_day_pct REAL,
        worst_day_pct REAL,
        expectancy_pct REAL,
        
        UNIQUE(symbol, strategy_name, timeframe, start_date, end_date),
        FOREIGN KEY (strategy_name) REFERENCES strategies(name)
    )
"""

# ============================================================================
# TABLE 2: backtest_trades
# ============================================================================
CREATE_BACKTEST_TRADES_TABLE = """
    CREATE TABLE IF NOT EXISTS backtest_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        
        -- Link to backtest_results
        backtest_result_id INTEGER,
        
        -- Trade Details
        entry_time TEXT NOT NULL,
        exit_time TEXT NOT NULL,
        symbol TEXT NOT NULL,
        entry_price REAL NOT NULL,
        exit_price REAL NOT NULL,
        volume REAL NOT NULL,
        
        -- P&L
        profit REAL NOT NULL,
        profit_pct REAL NOT NULL,
        
        -- Duration
        duration_hours REAL,
        
        -- Trade Type
        trade_type TEXT,  -- 'buy', 'sell'
        
        FOREIGN KEY (backtest_result_id) REFERENCES backtest_results(id)
    )
"""

# ============================================================================
# TABLE 3: rolling_metrics
# ============================================================================
CREATE_ROLLING_METRICS_TABLE = """
    CREATE TABLE IF NOT EXISTS rolling_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        
        -- Link to backtest_results
        backtest_result_id INTEGER,
        
        -- Date/Time
        date TEXT NOT NULL,
        
        -- Rolling Return Metrics
        rolling_6m_profit_pct REAL,
        rolling_12m_profit_pct REAL,
        rolling_18m_profit_pct REAL,
        
        -- Cumulative Metrics for that date
        cumulative_profit_pct REAL,
        cumulative_return REAL,
        
        -- Drawdown at that date
        drawdown_pct REAL,
        
        FOREIGN KEY (backtest_result_id) REFERENCES backtest_results(id),
        UNIQUE(backtest_result_id, date)
    )
"""

# ============================================================================
# INDEXES for Performance
# ============================================================================
CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_backtest_results_symbol_strategy ON backtest_results(symbol, strategy_name)",
    "CREATE INDEX IF NOT EXISTS idx_backtest_results_date ON backtest_results(created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_backtest_trades_result_id ON backtest_trades(backtest_result_id)",
    "CREATE INDEX IF NOT EXISTS idx_backtest_trades_symbol ON backtest_trades(symbol)",
    "CREATE INDEX IF NOT EXISTS idx_rolling_metrics_result_id ON rolling_metrics(backtest_result_id)",
    "CREATE INDEX IF NOT EXISTS idx_rolling_metrics_date ON rolling_metrics(date DESC)",
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_schema_creation_sql() -> list:
    """Get all SQL statements needed to create tables.

    Returns:
        List of SQL CREATE TABLE statements
    """
    return [
        CREATE_BACKTEST_RESULTS_TABLE,
        CREATE_BACKTEST_TRADES_TABLE,
        CREATE_ROLLING_METRICS_TABLE,
    ]


def get_indexes_sql() -> list:
    """Get all SQL statements needed to create indexes.

    Returns:
        List of SQL CREATE INDEX statements
    """
    return CREATE_INDEXES


def create_backtest_tables(db_connection) -> bool:
    """Create all backtest tables in database.

    Args:
        db_connection: SQLite connection object

    Returns:
        True if successful, False otherwise
    """
    try:
        cursor = db_connection.cursor()

        # Create tables
        for sql in get_schema_creation_sql():
            cursor.execute(sql)

        # Create indexes
        for sql in get_indexes_sql():
            cursor.execute(sql)

        db_connection.commit()
        return True
    except (sqlite3.Error, ValueError, TypeError) as e:
        print(f"Error creating backtest tables: {e}")
        return False
