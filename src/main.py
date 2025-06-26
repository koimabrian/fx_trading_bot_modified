# fx_trading_bot/src/main.py
# Purpose: Main entry point for the FX Trading Bot
import sys
import os
import time
import argparse

# Add the project root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.logger import setup_logging
from src.database.db_manager import DatabaseManager
from src.mt5_connector import MT5Connector
from src.strategy_manager import StrategyManager
from src.core.data_fetcher import DataFetcher
from src.core.trader import Trader
from src.core.trade_monitor import TradeMonitor
from src.ui.cli import setup_parser
from src.ui.gui.dashboard import Dashboard
from PyQt5.QtWidgets import QApplication

def main():
    # Setup logging
    setup_logging()

    # Parse arguments
    parser = setup_parser()
    args = parser.parse_args()

    # Initialize database
    db_path = os.path.join('src', 'data', 'market_data.sqlite')  # Normalize path
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = DatabaseManager(db_path)
    db.connect()
    db.create_tables()

    # Initialize MT5 connection
    mt5_conn = MT5Connector(db)
    if args.mode in ["live"]:
        if not mt5_conn.initialize():
            raise RuntimeError("Failed to initialize MT5 connection")

    # Initialize components
    strategy_manager = StrategyManager(db)
    data_fetcher = DataFetcher(mt5_conn, db)
    trader = Trader(strategy_manager, mt5_conn)
    trade_monitor = TradeMonitor(strategy_manager, mt5_conn)

    # Run the appropriate mode
    if args.mode == "live":
        while True:
            data_fetcher.sync_data()
            trader.execute_trades(args.strategy)
            trade_monitor.monitor_positions(args.strategy)
            time.sleep(20)
    elif args.mode == "gui":
        app = QApplication(sys.argv)
        dashboard = Dashboard(db)
        dashboard.show()
        sys.exit(app.exec_())
    else:
        raise ValueError("Invalid mode specified. Use 'live' or 'gui'.")

    db.close()

if __name__ == "__main__":
    main()