# fx_trading_bot/src/database/db_manager.py
# Purpose: Manages database connections and operations
import logging
import os
import sqlite3

from src.utils.logger import setup_logging

setup_logging()


class DatabaseManager:
    """Manages database connections and operations.

    Provides context manager interface for safe connection handling and
    delegates schema creation to DatabaseMigrations for centralized management.
    """

    def __init__(self, config):
        """Initialize DatabaseManager.

        Args:
            config: Configuration dictionary with database path, or direct path string
        """
        # Handle various config input formats
        if isinstance(config, str):
            # Direct path string
            self.db_path = config
            self.config = {}
        elif isinstance(config, dict):
            if "database" in config:
                # Config with nested database dict (typical from YAML)
                db_config = config["database"]
                if isinstance(db_config, dict):
                    self.db_path = db_config.get("path", "src/data/market_data.sqlite")
                else:
                    self.db_path = db_config
                self.config = config
            elif "path" in config:
                # Config with direct path key
                self.db_path = config.get("path", "src/data/market_data.sqlite")
                self.config = config
            else:
                # Assume string path encoded somehow
                self.db_path = "src/data/market_data.sqlite"
                self.config = config
        else:
            # Fallback
            self.db_path = "src/data/market_data.sqlite"
            self.config = {}

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
        """Establish database connection and ensure data directory exists.

        Checks if connection already exists to prevent duplicate connections.
        """
        try:
            # Skip if already connected
            if self.conn is not None:
                self.logger.debug("Database already connected, reusing connection")
                return

            # Auto-create data directory if it doesn't exist (skip for :memory:)
            if self.db_path != ":memory:":
                dir_path = os.path.dirname(self.db_path)
                if dir_path:  # Only create if there's a directory component
                    os.makedirs(dir_path, exist_ok=True)

            self.conn = sqlite3.connect(self.db_path)
            # Enable foreign keys and dictionary row access
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.row_factory = sqlite3.Row
            self.logger.debug("Database connection established: %s", self.db_path)
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
            return cursor
        except sqlite3.Error as e:
            self.logger.error("Query execution failed: %s, Error: %s", query, e)
            raise

    def create_tables(self):
        """Create necessary database tables and run migrations."""
        from src.database.migrations import DatabaseMigrations

        migrations = DatabaseMigrations(self.conn)
        result = migrations.create_tables() and migrations.create_indexes()
        # Run schema migrations
        if result:
            result = migrations.migrate()
        return result

    def create_indexes(self):
        """Create additional indexes on frequently queried columns."""
        from src.database.migrations import DatabaseMigrations

        migrations = DatabaseMigrations(self.conn)
        return migrations.create_indexes()
