# fx_trading_bot/src/main.py
# Purpose: Main entry point for the FX Trading Bot
import logging
import os
import sys
import time

import yaml

try:
    from PyQt5.QtWidgets import QApplication as QtApplication
except ImportError:
    QtApplication = None

from src.core.data_fetcher import DataFetcher
from src.core.trade_monitor import TradeMonitor
from src.core.trader import Trader
from src.database.db_manager import DatabaseManager
from src.mt5_connector import MT5Connector
from src.strategy_manager import StrategyManager
from src.ui.cli import setup_parser
from src.ui.gui.dashboard import Dashboard
from src.utils.data_validator import DataValidator
from src.utils.logger import setup_logging

# Add the project root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    """Main entry point for the FX Trading Bot.

    Initializes the database, loads configuration, and runs the bot in
    the specified mode (live trading, backtesting, or GUI dashboard).
    """
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    # Parse arguments
    parser = setup_parser()
    args = parser.parse_args()

    # Load config
    with open("src/config/config.yaml", "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    # Initialize database
    with DatabaseManager(config["database"]) as db:
        db.create_tables()
        db.create_indexes()

        # Validate and initialize data quality
        logger.info("Running data validation and initialization...")
        mt5_conn_temp = MT5Connector(db)
        validator = DataValidator(db, config, mt5_conn_temp)
        validator.validate_and_init()  # Auto-fill missing data (5000 rows per symbol/timeframe)

        # Initialize MT5 connection
        mt5_conn = MT5Connector(db)
        if args.mode == "live":
            if not mt5_conn.initialize():
                raise RuntimeError("Failed to initialize MT5 connection")

        # Initialize components
        strategy_manager = StrategyManager(db, mode=args.mode)
        data_fetcher = DataFetcher(mt5_conn, db, config)
        trader = Trader(strategy_manager, mt5_conn)
        trade_monitor = TradeMonitor(strategy_manager, mt5_conn)

        # Run the appropriate mode
        if args.mode == "live":
            logger.info("Starting live trading mode...")
            while True:
                # Use batch sync for parallel fetching (more efficient with multiple pairs)
                # Uncomment to use: data_fetcher.sync_data_batch()
                data_fetcher.sync_data()  # Sequential mode (works with single pair)
                trader.execute_trades(args.strategy)
                trade_monitor.monitor_positions(args.strategy)
                time.sleep(20)
        elif args.mode == "gui":
            logger.info("Launching GUI dashboard...")
            if QtApplication is None:
                logger.error("PyQt5 is not installed")
                return
            app = QtApplication(sys.argv)
            dashboard = Dashboard(db, config)
            dashboard.show()
            sys.exit(app.exec_())
        else:
            raise ValueError("Invalid mode specified. Use 'live' or 'gui'.")


if __name__ == "__main__":
    main()
