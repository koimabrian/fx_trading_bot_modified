"""Main entry point for the FX Trading Bot.

Orchestrates all operational modes: init, sync, backtest, live, gui, and test.
Implements the hybrid workflow with adaptive strategy selection, volatility
filtering, and comprehensive parameter archiving.
"""

import logging
import os
import sys
import subprocess
import time

import yaml

from src.core.adaptive_trader import AdaptiveTrader
from src.core.data_fetcher import DataFetcher
from src.core.init_manager import InitManager
from src.core.trade_monitor import TradeMonitor
from src.database.db_manager import DatabaseManager
from src.database.migrations import DatabaseMigrations
from src.backtesting.backtest_manager import BacktestManager
from src.mt5_connector import MT5Connector
from src.strategy_manager import StrategyManager
from src.ui.cli import setup_parser
from src.ui.web.dashboard_server import DashboardServer
from src.utils.data_validator import DataValidator
from src.utils.logger import setup_logging
from src.utils.live_trading_diagnostic import LiveTradingDiagnostic

# Add the project root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    """Main entry point for the FX Trading Bot.

    Handles 6 operational modes via CLI arguments:
    - init: Initialize database and populate tradable pairs
    - sync: Fetch/update market data from MT5
    - backtest: Run backtests with parameter optimization
    - live: Real-time trading with adaptive strategy selection
    - gui: Web dashboard for monitoring
    - test: Run comprehensive test suite
    """
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("FX Trading Bot - Adaptive Strategy Selection System")
    logger.info("=" * 70)

    # Parse arguments
    parser = setup_parser()
    args = parser.parse_args()

    # Load config
    try:
        with open("src/config/config.yaml", "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        logger.error("Configuration file not found: src/config/config.yaml")
        return
    except yaml.YAMLError as e:
        logger.error("Failed to parse configuration: %s", e)
        return

    # Auto-generate pairs from pair_config
    generate_pairs_from_config(config)

    # Route to appropriate mode handler
    if args.mode == "init":
        _mode_init(config, logger)
    elif args.mode == "sync":
        _mode_sync(config, args, logger)
    elif args.mode == "backtest":
        _mode_backtest(config, args, logger)
    elif args.mode == "live":
        _mode_live(config, args, logger)
    elif args.mode == "gui":
        _mode_gui(config, args, logger)
    elif args.mode == "test":
        _mode_test(logger)
    else:
        logger.error("Unknown mode: %s", args.mode)


def _mode_init(config: dict, logger):
    """Execute init mode: Initialize database and populate pairs."""
    logger.info("MODE: init - Initializing database and loading pairs...")
    try:
        with DatabaseManager(config["database"]) as db:
            # Run migrations
            migrations = DatabaseMigrations(db.conn)
            if not migrations.migrate_tables():
                logger.error("Database migration failed")
                return

            # Initialize MT5 and populate pairs
            mt5_conn = MT5Connector(db)
            if not mt5_conn.initialize():
                logger.error("Failed to initialize MT5 connection")
                return

            init_manager = InitManager(db, mt5_conn, config)
            if init_manager.run_initialization():
                logger.info("Initialization completed successfully")
            else:
                logger.error("Initialization failed")

    except (KeyError, ValueError, TypeError, OSError) as e:
        logger.error("Init mode failed: %s", e)


def _mode_sync(config: dict, args, logger):
    """Execute sync mode: Synchronize market data from MT5."""
    logger.info("MODE: sync - Synchronizing market data...")
    try:
        with DatabaseManager(config["database"]) as db:
            # Setup database
            migrations = DatabaseMigrations(db.conn)
            migrations.migrate_tables()

            # Initialize MT5
            mt5_conn = MT5Connector(db)
            if not mt5_conn.initialize():
                logger.error("Failed to initialize MT5 for sync")
                return

            # Sync data
            validator = DataValidator(db, config, mt5_conn)
            if args.symbol:
                logger.info("Syncing data for symbol: %s", args.symbol)
                validator.sync_data(args.symbol, None)
            else:
                logger.info("Syncing data for all configured symbols...")
                # Read from tradable_pairs (selected during init) instead of config
                cursor = db.conn.cursor()
                cursor.execute("SELECT symbol FROM tradable_pairs ORDER BY symbol")
                symbols = [row[0] for row in cursor.fetchall()]

                if not symbols:
                    logger.warning(
                        "No symbols found in tradable_pairs. Run init mode first."
                    )
                else:
                    for symbol in symbols:
                        logger.info("  Syncing: %s", symbol)
                        validator.sync_data(symbol, None)

            logger.info("Data sync completed successfully")

    except (OSError, RuntimeError, ValueError) as e:
        logger.error("Sync mode failed: %s", e)


def _mode_backtest(config: dict, args, logger):
    """Execute backtest mode: Run backtests with parameter optimization."""
    logger.info("MODE: backtest - Running backtests and optimization...")
    try:
        with DatabaseManager(config["database"]) as db:
            # Setup database
            migrations = DatabaseMigrations(db.conn)
            migrations.migrate_tables()

            # Run backtests
            backtest_manager = BacktestManager(config)
            if args.symbol:
                logger.info("Backtesting symbol: %s", args.symbol)
                backtest_manager.run_backtest(
                    symbol=args.symbol, strategy_name=args.strategy
                )
            else:
                logger.info("Backtesting all configured symbols and strategies...")
                if args.strategy:
                    backtest_manager.run_backtest(strategy_name=args.strategy)
                else:
                    backtest_manager.run_backtest()

            logger.info("Backtesting completed successfully")

    except (OSError, RuntimeError, ValueError) as e:
        logger.error("Backtest mode failed: %s", e)


def _display_optimal_parameters(db, logger):
    """Display optimal parameters from database in a formatted table."""
    try:
        results = db.execute_query(
            "SELECT op.strategy_name, tp.symbol, op.timeframe, op.parameter_value "
            "FROM optimal_parameters op "
            "JOIN tradable_pairs tp ON op.symbol_id = tp.id "
            "ORDER BY op.strategy_name, tp.symbol, op.timeframe"
        ).fetchall()

        if not results:
            logger.info(
                "\n[INFO] No optimal parameters found - run backtest mode first"
            )
            return

        # Group by strategy for display
        strategies = {}
        for row in results:
            strategy_name = row[0]
            symbol = row[1]
            timeframe = row[2]
            params_str = row[3]

            if strategy_name not in strategies:
                strategies[strategy_name] = []

            strategies[strategy_name].append(
                {"symbol": symbol, "timeframe": timeframe, "params": params_str}
            )

        # Display header
        logger.info("\n" + "=" * 80)
        logger.info("OPTIMAL PARAMETERS FROM BACKTESTING")
        logger.info("=" * 80)

        # Display each strategy
        for strategy_name, entries in sorted(strategies.items()):
            logger.info(f"\n[{strategy_name.upper()}] ({len(entries)} parameter sets)")
            logger.info("-" * 80)
            for entry in entries:
                # Handle both numeric (15, 60, 240) and string (M15, H1, H4) timeframes
                tf = entry["timeframe"]
                if isinstance(tf, str):
                    # Already in string format (M15, H1, etc)
                    timeframe_str = tf
                else:
                    # Numeric format - convert to string
                    tf_num = int(tf)
                    timeframe_str = f"M{tf_num}" if tf_num < 60 else f"H{tf_num // 60}"
                logger.info(f"  {entry['symbol']} ({timeframe_str}): {entry['params']}")

        logger.info("=" * 80 + "\n")

    except Exception as e:
        logger.debug(f"Could not display optimal parameters: {e}")


def _mode_live(config: dict, args, logger):
    """Execute live mode: Real-time trading with adaptive strategy selection."""
    logger.info("MODE: live - Starting live trading...")
    try:
        with DatabaseManager(config["database"]) as db:
            # Setup database
            migrations = DatabaseMigrations(db.conn)
            migrations.migrate_tables()

            # Initialize MT5
            mt5_conn = MT5Connector(db)
            if not mt5_conn.initialize():
                logger.error("Failed to initialize MT5 for live trading")
                return

            # RUN DIAGNOSTICS FIRST
            logger.info("=" * 70)
            logger.info("Running live trading diagnostics...")
            logger.info("=" * 70)
            diagnostic = LiveTradingDiagnostic(config, db, mt5_conn)
            report = diagnostic.run_full_diagnostic()

            if not report["can_trade"]:
                logger.error("\n" + LiveTradingDiagnostic.get_blockers_summary(report))
                logger.error("Live trading cannot proceed. Fix issues above and retry.")
                return

            logger.info(
                "\n[OK] All diagnostics passed - proceeding with live trading\n"
            )

            # Initialize components
            try:
                strategy_manager = StrategyManager(db, mode="live", symbol=args.symbol)
                logger.debug("StrategyManager initialized")
            except Exception as e:
                logger.error(
                    "Failed to initialize StrategyManager: %s", e, exc_info=True
                )
                return

            try:
                data_fetcher = DataFetcher(mt5_conn, db, config)
                logger.debug("DataFetcher initialized")
            except Exception as e:
                logger.error("Failed to initialize DataFetcher: %s", e, exc_info=True)
                return

            try:
                adaptive_trader = AdaptiveTrader(strategy_manager, mt5_conn, db)
                logger.debug("AdaptiveTrader initialized")
            except Exception as e:
                logger.error(
                    "Failed to initialize AdaptiveTrader: %s", e, exc_info=True
                )
                return

            try:
                trade_monitor = TradeMonitor(strategy_manager, mt5_conn)
                logger.debug("TradeMonitor initialized")
            except Exception as e:
                logger.error("Failed to initialize TradeMonitor: %s", e, exc_info=True)
                return

            # Display optimal parameters
            try:
                _display_optimal_parameters(db, logger)
            except Exception as e:
                logger.debug("Could not display optimal parameters: %s", e)

            # Determine trading mode
            use_adaptive = args.strategy is None

            if use_adaptive:
                logger.info("Adaptive strategy selection: ENABLED")
            else:
                logger.info("Fixed strategy mode: %s", args.strategy)

            # Load pairs for trading
            pairs_to_trade = []
            if args.symbol:
                logger.info("Trading symbol: %s", args.symbol)
                pairs_to_trade = [args.symbol]
            else:
                # Load from database or config
                try:
                    cursor = db.conn.cursor()
                    cursor.execute(
                        "SELECT DISTINCT symbol FROM tradable_pairs ORDER BY symbol"
                    )
                    pairs_to_trade = [row[0] for row in cursor.fetchall()]
                    if pairs_to_trade:
                        logger.info(
                            "Trading all configured pairs (volatility filtered): %s",
                            ", ".join(pairs_to_trade),
                        )
                    else:
                        logger.warning(
                            "No pairs found in database. Using config pairs."
                        )
                        pairs_to_trade = [p["symbol"] for p in config.get("pairs", [])]
                except Exception as e:
                    logger.warning("Could not load pairs from database: %s", e)
                    pairs_to_trade = [p["symbol"] for p in config.get("pairs", [])]

            if not pairs_to_trade:
                logger.error(
                    "No trading pairs configured. Initialize with: python -m src.main --mode init"
                )
                return

            # Populate config pairs for DataFetcher to use
            timeframes = config.get("pair_config", {}).get("timeframes", [15, 60, 240])
            config["pairs"] = [
                {"symbol": sym, "timeframe": tf}
                for sym in pairs_to_trade
                for tf in timeframes
            ]

            # Main trading loop
            last_incremental_sync = 0
            incremental_sync_interval = (
                config.get("sync", {}).get("incremental_interval_min", 4) * 60
            )

            logger.info("=" * 70)
            logger.info("LIVE TRADING STARTED")
            logger.info("=" * 70)

            loop_iteration = 0
            while True:
                try:
                    loop_iteration += 1
                    current_time = time.time()

                    # Data synchronization
                    fetch_count = config.get("data", {}).get("fetch_count", 2000)
                    has_sufficient_data = data_fetcher.has_sufficient_data(
                        fetch_count, symbol=args.symbol
                    )
                    time_since_last_sync = current_time - last_incremental_sync

                    if not has_sufficient_data:
                        logger.debug("Insufficient data - performing full sync")
                        data_fetcher.sync_data(symbol=args.symbol)
                        last_incremental_sync = current_time
                    elif time_since_last_sync >= incremental_sync_interval:
                        logger.debug("Incremental sync interval reached")
                        data_fetcher.sync_data_incremental(symbol=args.symbol)
                        last_incremental_sync = current_time

                    # Collect signals from all trading pairs
                    all_signals = []
                    executed_trades = []
                    failed_trades = []

                    # Execute trades for each configured pair
                    if use_adaptive:
                        for symbol in pairs_to_trade:
                            signals = adaptive_trader.get_signals_adaptive(symbol)
                            if signals:
                                all_signals.extend(signals)
                                # Execute each signal as a trade order
                                for signal in signals:
                                    try:
                                        strategy_name = signal.get(
                                            "strategy_info", {}
                                        ).get("name", "adaptive")

                                        # Place the actual trade order
                                        if mt5_conn.place_order(signal, strategy_name):
                                            executed_trades.append(
                                                {
                                                    "symbol": signal.get("symbol"),
                                                    "action": signal.get("action"),
                                                    "strategy": strategy_name,
                                                    "timeframe": signal.get(
                                                        "timeframe"
                                                    ),
                                                    "confidence": signal.get(
                                                        "confidence", 0
                                                    ),
                                                    "status": "executed",
                                                    "timestamp": time.time(),
                                                }
                                            )
                                            logger.info(
                                                f"[EXECUTED] Trade placed: {signal.get('symbol')} {signal.get('action').upper()} "
                                                f"(Strategy: {strategy_name}, Confidence: {signal.get('confidence', 0):.2f})"
                                            )
                                        else:
                                            failed_trades.append(
                                                {
                                                    "symbol": signal.get("symbol"),
                                                    "action": signal.get("action"),
                                                    "strategy": strategy_name,
                                                    "reason": "MT5 order placement failed",
                                                }
                                            )
                                            logger.error(
                                                f"[FAILED] Trade placement failed: {signal.get('symbol')} {signal.get('action').upper()} "
                                                f"(Strategy: {strategy_name})"
                                            )
                                    except Exception as e:
                                        failed_trades.append(
                                            {
                                                "symbol": signal.get("symbol"),
                                                "action": signal.get("action"),
                                                "reason": str(e),
                                            }
                                        )
                                        logger.error(
                                            f"[FAILED] Exception placing trade for {symbol}: {e}"
                                        )
                    else:
                        signals = strategy_manager.generate_signals(args.strategy)
                        if signals:
                            all_signals.extend(signals)

                    # Ensure all_signals is a list (never None)
                    if all_signals is None:
                        all_signals = []

                    if all_signals:
                        logger.info(
                            f"[Loop {loop_iteration}] Generated {len(all_signals)} signals from {len(pairs_to_trade)} pairs"
                        )
                        for signal in all_signals:
                            logger.info(f"  Signal: {signal}")
                            # Log trade signal to database
                            try:
                                cursor = db.conn.cursor()
                                symbol = signal.get("symbol", "UNKNOWN")

                                # Get symbol_id from tradable_pairs table
                                cursor.execute(
                                    "SELECT id FROM tradable_pairs WHERE symbol = ?",
                                    (symbol,),
                                )
                                result = cursor.fetchone()
                                symbol_id = result[0] if result else None

                                if symbol_id:
                                    cursor.execute(
                                        """INSERT INTO trades 
                                        (symbol_id, timeframe, strategy_name, trade_type, volume, 
                                         open_price, status, open_time)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                                        (
                                            symbol_id,
                                            signal.get("timeframe"),
                                            signal.get("strategy_info", {}).get(
                                                "name", "unknown"
                                            ),
                                            signal.get("action", "unknown"),
                                            signal.get("volume", 0.01),
                                            0.0,  # Entry price would be filled on execution
                                            "signal_generated",
                                        ),
                                    )
                                    db.conn.commit()
                            except Exception as e:
                                logger.debug(f"Could not log trade signal: {e}")

                    else:
                        logger.debug(
                            f"[Loop {loop_iteration}] No signals generated from {len(pairs_to_trade)} pairs"
                        )

                    # Log execution statistics
                    if executed_trades or failed_trades:
                        logger.info("=" * 70)
                        logger.info(f"TRADE EXECUTION SUMMARY (Loop {loop_iteration}):")
                        logger.info(
                            f"  [EXECUTED] Successful: {len(executed_trades)} trades"
                        )
                        if executed_trades:
                            for trade in executed_trades:
                                logger.info(
                                    f"    - {trade['symbol']} {trade['action']} ({trade['strategy']})"
                                )
                        logger.info(f"  [FAILED] Failed: {len(failed_trades)} trades")
                        if failed_trades:
                            for trade in failed_trades:
                                logger.info(
                                    f"    - {trade['symbol']} {trade['action']} ({trade.get('reason', 'unknown')})"
                                )
                        logger.info("=" * 70)

                    # Sleep before next iteration
                    time.sleep(20)  # Check every 20 seconds

                except (KeyboardInterrupt, SystemExit):
                    logger.info("Live trading stopped by user")
                    break
                except Exception as e:
                    logger.error(f"Error in trading loop: {e}", exc_info=True)
                    time.sleep(10)  # Wait before retrying

            logger.info("=" * 70)
            logger.info("LIVE TRADING STOPPED")
            logger.info("=" * 70)

    except (KeyError, ValueError, TypeError, OSError) as e:
        logger.error("Live mode failed: %s", e)


def _mode_gui(config: dict, args, logger):
    """Execute GUI mode: Launch web dashboard."""
    logger.info("MODE: gui - Launching web dashboard...")
    try:
        with DatabaseManager(config["database"]) as db:
            # Setup database (read-only)
            migrations = DatabaseMigrations(db.conn)
            migrations.migrate_tables()

            # Launch dashboard
            host = args.host or config.get("gui", {}).get("host", "127.0.0.1")
            port = args.port or config.get("gui", {}).get("port", 5000)

            logger.info("Dashboard URL: http://%s:%d", host, port)
            logger.info("Press Ctrl+C to stop the server")

            dashboard = DashboardServer(config, host=host, port=port)
            dashboard.run(debug=False)

    except (OSError, RuntimeError, ValueError) as e:
        logger.error("GUI mode failed: %s", e)


def _mode_test(logger):
    """Execute test mode: Run comprehensive test suite."""
    logger.info("MODE: test - Running test suite...")
    try:
        result = subprocess.run(["pytest", "tests/", "-v"], check=False)
        if result.returncode == 0:
            logger.info("All tests passed successfully")
        else:
            logger.error("Some tests failed (exit code: %d)", result.returncode)

    except FileNotFoundError:
        logger.error("pytest not found - install with: pip install pytest")
    except (OSError, RuntimeError) as e:
        logger.error("Test mode failed: %s", e)


def generate_pairs_from_config(config):
    """Auto-generate flat pairs list from pair_config categories.

    Converts the nested pair_config structure into a flat list of pairs
    for backward compatibility with existing code.
    """
    if "pair_config" not in config:
        return

    pair_config = config["pair_config"]
    if not pair_config:
        return

    timeframes = pair_config.get("timeframes", [15, 60])
    categories = pair_config.get("categories", {})

    if not categories:
        return

    pairs = []
    for _category, data in categories.items():
        if data is None:
            continue
        symbols = data.get("symbols", []) if isinstance(data, dict) else data
        if symbols is None:
            continue
        for symbol in symbols:
            for timeframe in timeframes:
                pairs.append({"symbol": symbol, "timeframe": timeframe})

    config["pairs"] = pairs
    logger = logging.getLogger(__name__)
    if pairs:
        logger.info(
            "Generated %d pairs from pair_config (%d symbols × %d timeframes)",
            len(pairs),
            sum(
                len(data.get("symbols", data) if isinstance(data, dict) else data or [])
                for data in categories.values()
                if data and (data.get("symbols") or data)
            ),
            len(timeframes),
        )
    else:
        logger.debug(
            "No pairs defined in pair_config (optional - will use MT5 auto-discovery)"
        )


if __name__ == "__main__":
    main()
