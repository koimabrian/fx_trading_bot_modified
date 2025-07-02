# src/main.py
# Purpose: Main entry point for the FX Trading Bot
import sys
import os
import argparse
import yaml
from src.utils.logger import setup_logging
from src.database.db_manager import DatabaseManager
from src.mt5_connector import MT5Connector
from src.strategy_manager import StrategyManager
from src.core.bot_runner import LiveBotRunner, BacktestBotRunner
from src.ui.cli import setup_parser
from src.ui.gui.dashboard import Dashboard
from PyQt5.QtWidgets import QApplication

def main():
    setup_logging()
    parser = setup_parser()
    args = parser.parse_args()
    with open('src/config/config.yaml', 'r') as file:
        config = yaml.safe_load(file)
    db_path = config['database']['live_path'] if args.mode in ['live', 'gui'] else config['database']['backtest_path']
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = DatabaseManager({'path': db_path})
    db.connect()
    mt5_conn = MT5Connector(db, config)
    strategy_manager = StrategyManager(db, config, mode=args.mode if args.mode in ['live', 'backtest'] else 'live')
    if args.mode == 'live':
        runner = LiveBotRunner(db, mt5_conn, strategy_manager, config)
        runner.run(args)
    elif args.mode == 'backtest':
        runner = BacktestBotRunner(db, mt5_conn, strategy_manager, config)
        runner.run(args)
    elif args.mode == 'gui':
        app = QApplication(sys.argv)
        dashboard = Dashboard(db)
        dashboard.show()
        sys.exit(app.exec_())
    else:
        raise ValueError("Invalid mode specified. Use 'live', 'backtest', or 'gui'.")
    db.close()

if __name__ == "__main__":
    main()