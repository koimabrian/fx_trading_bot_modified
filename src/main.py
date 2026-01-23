"""Main entry point for the FX Trading Bot.

Handles three operational modes:
- sync: Fetches market data from MT5
- backtest: Runs strategy backtests
- live: Executes trades with adaptive strategy selection
- gui: Web-based dashboard served to browser
"""

import logging
import os
import sys
import time

import yaml

from src.core.adaptive_trader import AdaptiveTrader
from src.core.data_fetcher import DataFetcher
from src.core.trade_monitor import TradeMonitor
from src.core.trader import Trader
from src.database.db_manager import DatabaseManager
from src.mt5_connector import MT5Connector
from src.strategy_manager import StrategyManager
from src.ui.cli import setup_parser
from src.ui.web.dashboard_server import DashboardServer
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

    # Auto-generate pairs from pair_config if not already populated
    generate_pairs_from_config(config)

    # Handle sync mode early (data sync only)
    if args.mode == "sync":
        logger.info("Starting data sync mode...")
        with DatabaseManager(config["database"]) as db:
            db.create_tables()
            db.create_indexes()

            # Initialize MT5 connection for data fetching
            mt5_conn = MT5Connector(db)
            if not mt5_conn.initialize():
                logger.error(
                    "Failed to initialize MT5 for sync. Check credentials and terminal."
                )
                return

            # Initialize data fetcher and validator
            validator = DataValidator(db, config, mt5_conn)

            # Sync specific symbol or all symbols
            if args.symbol:
                logger.info("Syncing data for symbol: %s", args.symbol)
                validator.sync_data(args.symbol, None)  # pylint: disable=no-member
            else:
                logger.info("Syncing data for all configured symbols...")
                symbols = sorted(set(p["symbol"] for p in config.get("pairs", [])))
                for symbol in symbols:
                    logger.info("Syncing symbol: %s", symbol)
                    validator.sync_data(symbol, None)  # pylint: disable=no-member

            logger.info("Data sync completed successfully")
        return

    # Initialize database
    with DatabaseManager(config["database"]) as db:
        db.create_tables()
        db.create_indexes()

        # Validate and initialize data quality (for live modes only, not GUI)
        # GUI mode only reads existing data, doesn't need MT5 connection
        if args.mode != "gui":
            logger.info("Running data validation and initialization...")
            mt5_conn_temp = MT5Connector(db)
            validator = DataValidator(db, config, mt5_conn_temp)
            validator.validate_and_init(symbol=args.symbol)  # Pass symbol parameter

        # Initialize MT5 connection
        mt5_conn = MT5Connector(db)
        if args.mode == "live":
            if not mt5_conn.initialize():
                raise RuntimeError("Failed to initialize MT5 connection")

        # Initialize components
        strategy_manager = StrategyManager(db, mode=args.mode, symbol=args.symbol)
        data_fetcher = DataFetcher(mt5_conn, db, config)
        trader = Trader(strategy_manager, mt5_conn)
        adaptive_trader = AdaptiveTrader(strategy_manager, mt5_conn, db)
        trade_monitor = TradeMonitor(strategy_manager, mt5_conn)

        # Run the appropriate mode
        if args.mode == "live":
            logger.info("Starting live trading mode...")

            # Determine if using adaptive trading:
            # - Use adaptive if NO --strategy specified AND no --symbol specified (all symbols)
            # - Use fixed strategy if --strategy is specified OR only one symbol is specified
            use_adaptive = args.strategy is None and not args.symbol

            if use_adaptive:
                logger.info(
                    "Adaptive strategy selection enabled (no --strategy, trading all symbols)"
                )
            elif args.strategy:
                logger.info("Fixed strategy mode: using %s", args.strategy)
            else:
                logger.info(
                    "Fixed strategy mode: trading single symbol %s", args.symbol
                )

            if args.symbol:
                logger.info("Trading specific symbol: %s", args.symbol)
            else:
                logger.info("Trading all configured symbols")

            # Separate timer for incremental sync (every 4 minutes instead of every 20 seconds)
            last_incremental_sync = 0
            incremental_sync_interval = 240  # 4 minutes in seconds

            while True:
                current_time = time.time()

                # Conditional sync strategy:
                # 1. If no data exists → Full sync (fetch_count rows) to initialize
                # 2. If data >= fetch_count AND 4 minutes elapsed → Incremental sync (only new rows since last timestamp)
                fetch_count = config.get("data", {}).get("fetch_count", 2000)
                has_sufficient_data = data_fetcher.has_sufficient_data(
                    fetch_count, symbol=args.symbol
                )
                time_since_last_sync = current_time - last_incremental_sync

                if not has_sufficient_data:
                    data_fetcher.sync_data(
                        symbol=args.symbol
                    )  # Full sync to initialize (respects --symbol)
                    last_incremental_sync = current_time  # Reset timer after full sync
                elif time_since_last_sync >= incremental_sync_interval:
                    logger.info("4 minutes elapsed - performing incremental sync")
                    data_fetcher.sync_data_incremental(
                        symbol=args.symbol
                    )  # Only fetch new rows (respects --symbol)
                    last_incremental_sync = current_time  # Update timer

                # Execute trades based on mode (runs every 20 seconds)
                if use_adaptive:
                    adaptive_trader.execute_adaptive_trades(symbol=args.symbol)
                else:
                    trader.execute_trades(args.strategy)
                trade_monitor.monitor_positions(args.strategy)
                time.sleep(20)
        elif args.mode == "gui":
            logger.info("Launching web dashboard...")
            host = config.get("web", {}).get("host", "127.0.0.1")
            port = config.get("web", {}).get("port", 2000)
            dashboard = DashboardServer(config, host=host, port=port)
            dashboard.run(debug=False)
        else:
            raise ValueError("Invalid mode specified. Use 'sync', 'live', or 'gui'.")


def generate_pairs_from_config(config):
    """Auto-generate flat pairs list from pair_config categories.

    Converts the nested pair_config structure into a flat list of pairs
    for backward compatibility with existing code.
    """
    if "pair_config" not in config:
        return

    pair_config = config["pair_config"]
    timeframes = pair_config.get("timeframes", [15, 60])
    categories = pair_config.get("categories", {})

    pairs = []
    for _category, data in categories.items():
        symbols = data.get("symbols", []) if isinstance(data, dict) else data
        for symbol in symbols:
            for timeframe in timeframes:
                pairs.append({"symbol": symbol, "timeframe": timeframe})

    config["pairs"] = pairs
    logger = logging.getLogger(__name__)
    logger.info(
        "Generated %d pairs from pair_config (%d symbols × %d timeframes)",
        len(pairs),
        sum(
            len(data.get("symbols", data) if isinstance(data, dict) else data)
            for data in categories.values()
        ),
        len(timeframes),
    )


if __name__ == "__main__":
    main()
