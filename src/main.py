"""Main entry point for the FX Trading Bot.

Orchestrates all operational modes: init, sync, backtest, live, gui, and test.
Implements the hybrid workflow with adaptive strategy selection, volatility
filtering, and comprehensive parameter archiving.
"""

import datetime
import os
import sqlite3
import subprocess
import sys
import time

import MetaTrader5 as mt5
from PyQt5.QtWidgets import QApplication

from src.backtesting.backtest_manager import BacktestManager
from src.core.adaptive_trader import AdaptiveTrader
from src.core.data_fetcher import DataFetcher
from src.core.trade_monitor import TradeMonitor
from src.database.db_manager import DatabaseManager
from src.database.migrations import DatabaseMigrations
from src.core.mt5_connector import MT5Connector
from src.core.strategy_manager import StrategyManager
from src.ui.cli import setup_parser
from src.ui.gui.init_wizard_dialog import InitWizardDialog
from src.ui.web.dashboard_server import DashboardServer
from src.utils.config_manager import ConfigManager
from src.utils.data_validator import DataValidator
from src.utils.live_trading_diagnostic import LiveTradingDiagnostic
from src.utils.logging_factory import LoggingFactory

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
    # Parse arguments first to get the mode
    parser = setup_parser()
    args = parser.parse_args()

    # Setup logging with mode-specific log file (cleared on each run)
    LoggingFactory.configure(level="INFO", log_dir="logs", mode=args.mode)
    logger = LoggingFactory.get_logger(__name__)

    logger.info("=" * 70)
    logger.info("FX Trading Bot - Adaptive Strategy Selection System")
    logger.info("=" * 70)

    # Load config
    try:
        config = ConfigManager.get_config()
    except Exception as e:
        logger.error("Failed to load configuration: %s", e)
        return

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
    """Execute init mode: Initialize database via PyQt5 GUI wizard.

    The initialization wizard is a multi-step PyQt5 dialog that guides users
    through database setup, MT5 connection, symbol discovery, and symbol
    selection. All symbol selection is done via GUI (not config).

    Args:
        config: Application configuration dictionary.
        logger: Logger instance for output messages.
    """
    logger.info("MODE: init - Starting initialization wizard...")
    try:
        # Create Qt application for GUI
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Show initialization wizard
        wizard = InitWizardDialog(config)
        if wizard.exec_() == wizard.Accepted:
            logger.info("Initialization completed successfully")
        else:
            logger.warning("Initialization cancelled by user")

    except Exception as e:
        logger.error("Init mode failed: %s", e)


def _mode_sync(config: dict, args, logger):
    """Execute sync mode: Synchronize market data and trade history from MT5.

    Args:
        config: Application configuration dictionary.
        args: Parsed command-line arguments.
        logger: Logger instance for output messages.
    """
    logger.info("MODE: sync - Synchronizing market data and trade history...")
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

            # Sync market data
            logger.info("=" * 60)
            logger.info("PHASE 1: Syncing market data from MT5...")
            logger.info("=" * 60)
            
            validator = DataValidator(db, config, mt5_conn)
            if args.symbol:
                logger.info("Syncing data for symbol: %s", args.symbol)
                validator.sync_data(args.symbol, None)
            else:
                logger.info("Syncing data for all configured symbols...")
                # Read from tradable_pairs (selected during init) instead of config
                symbols = db.get_all_symbols()

                if not symbols:
                    logger.warning(
                        "No symbols found in tradable_pairs. Run init mode first."
                    )
                else:
                    for symbol in symbols:
                        logger.info("  Syncing: %s", symbol)
                        validator.sync_data(symbol, None)

            logger.info("Market data sync completed successfully")
            
            # Sync trade history from MT5
            logger.info("")
            logger.info("=" * 60)
            logger.info("PHASE 2: Syncing trade history from MT5...")
            logger.info("=" * 60)
            
            from src.core.trade_syncer import TradeSyncer
            trade_syncer = TradeSyncer(db, mt5_conn)
            
            # Sync deals and orders (30 days by default)
            deals_synced = trade_syncer.sync_deals_from_mt5(days_back=30)
            orders_synced = trade_syncer.sync_orders_from_mt5(days_back=30)
            positions_synced = trade_syncer.sync_open_positions()
            
            # Reconcile open positions
            reconciliation = trade_syncer.reconcile_with_database()
            
            logger.info("")
            logger.info("Trade sync summary:")
            logger.info(f"  - Deals synced: {deals_synced}")
            logger.info(f"  - Orders synced: {orders_synced}")
            logger.info(f"  - Open positions synced: {positions_synced}")
            logger.info(f"  - Positions closed in MT5: {len(reconciliation['closed_in_mt5'])}")
            logger.info(f"  - New positions added to DB: {len(reconciliation['missing_in_db'])}")
            
            logger.info("")
            logger.info("=" * 60)
            logger.info("All sync operations completed successfully")
            logger.info("=" * 60)

    except (OSError, RuntimeError, ValueError) as e:
        logger.error("Sync mode failed: %s", e)


def _mode_backtest(config: dict, args, logger):
    """Execute backtest mode: Run backtests with parameter optimization.

    Args:
        config: Application configuration dictionary.
        args: Parsed command-line arguments.
        logger: Logger instance for output messages.
    """
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
    """Display optimal parameters from database in a formatted table.

    Args:
        db: Database manager instance.
        logger: Logger instance for output messages.
    """
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
    """Execute live mode: Real-time trading with adaptive strategy selection.

    Args:
        config: Application configuration dictionary.
        args: Parsed command-line arguments.
        logger: Logger instance for output messages.
    """
    logger.info("MODE: live - Starting live trading...")
    try:
        with DatabaseManager(config["database"]) as db:
            # Setup database
            migrations = DatabaseMigrations(db.conn)
            migrations.migrate_tables()

            # Clean up live_trades table on live start
            logger.info("Cleaning up live_trades table...")
            try:
                query = "DELETE FROM live_trades"
                db.execute_query(query)
                logger.info(
                    "Live trades table cleared - ready for fresh live trading session"
                )
            except sqlite3.Error as e:
                logger.warning("Could not clear live_trades table: %s", e)

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

            # Load pairs for trading FIRST (before StrategyManager)
            pairs_to_trade = []
            if args.symbol:
                logger.info("Trading symbol: %s", args.symbol)
                pairs_to_trade = [args.symbol]
            else:
                # Try database first, then fallback to config
                try:
                    query = "SELECT DISTINCT symbol FROM tradable_pairs ORDER BY symbol"
                    rows = db.execute_query(query).fetchall()
                    db_pairs = [row[0] for row in rows]
                    if db_pairs:
                        pairs_to_trade = db_pairs
                        logger.info(
                            "Loaded %d trading pairs from database (volatility filtered): %s",
                            len(pairs_to_trade),
                            ", ".join(pairs_to_trade),
                        )
                    else:
                        # DB table exists but empty
                        logger.error("No trading pairs found in database")
                        pairs_to_trade = []
                except (sqlite3.Error, AttributeError) as e:
                    # DB query failed
                    logger.error("Could not load pairs from database: %s", e)
                    pairs_to_trade = []

            if not pairs_to_trade:
                logger.error(
                    "No trading pairs available. Initialize with: python -m src.main --mode init"
                )
                return

            # Populate config pairs BEFORE StrategyManager initialization
            timeframes = config.get("timeframes", [15, 60, 240])
            config["pairs"] = [
                {"symbol": sym, "timeframe": tf}
                for sym in pairs_to_trade
                for tf in timeframes
            ]
            logger.debug(
                "Configured %d pair/timeframe combinations", len(config["pairs"])
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

            # Helper function to calculate dynamic lot size
            def calculate_lot_size(signal, account_balance, config):
                """Calculate position size based on confidence and account balance.

                Args:
                    signal: Trade signal dict with 'confidence' field
                    account_balance: Current account balance
                    config: Config dict with lot_size parameters

                Returns:
                    Lot size (volume) scaled by confidence and account balance
                """
                base_lot = config.get("risk_management", {}).get("lot_size", 0.01)
                min_lot = config.get("risk_management", {}).get("lot_size_min", 0.005)
                max_lot = config.get("risk_management", {}).get("lot_size_max", 0.05)
                scale_confidence = config.get("risk_management", {}).get(
                    "scale_by_confidence", True
                )
                scale_balance = config.get("risk_management", {}).get(
                    "scale_by_account_balance", True
                )
                confidence_mult = config.get("risk_management", {}).get(
                    "confidence_multiplier", 2.0
                )

                lot_size = base_lot

                # Scale by signal confidence (0.5-1.0 range)
                if scale_confidence:
                    confidence = signal.get("confidence", 0.5)
                    # Map 0.5-1.0 to 1.0-2.0 multiplier
                    confidence_factor = 1.0 + (confidence - 0.5) * confidence_mult
                    lot_size *= confidence_factor

                # Scale by account balance (normalize to 10000 baseline)
                if scale_balance:
                    balance_factor = max(
                        account_balance / 10000.0, 0.5
                    )  # Never go below 50%
                    lot_size *= balance_factor

                # Enforce limits
                lot_size = max(min_lot, min(lot_size, max_lot))

                logger.debug(
                    "Lot size: %.4f (base: %.4f, confidence: %.2f, balance: $%.2f, factors: conf=%.2f, bal=%.2f)",
                    lot_size,
                    base_lot,
                    signal.get("confidence", 0.5),
                    account_balance,
                    (
                        (1.0 + (signal.get("confidence", 0.5) - 0.5) * confidence_mult)
                        if scale_confidence
                        else 1.0
                    ),
                    (max(account_balance / 10000.0, 0.5)) if scale_balance else 1.0,
                )
                return lot_size

            # Main trading loop
            last_incremental_sync = 0
            incremental_sync_interval = (
                config.get("sync", {}).get("incremental_interval_min", 4) * 60
            )

            # Signal deduplication: track recently generated signals (last 60 seconds)
            recent_signals = {}  # Format: "SYMBOL_ACTION_TIMEFRAME" -> timestamp

            # Daily loss tracking
            trading_day_start = datetime.datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            daily_loss = 0.0
            daily_loss_limit = config.get("risk_management", {}).get(
                "daily_loss_limit", 100.0
            )

            logger.info("=" * 70)
            logger.info("LIVE TRADING STARTED")
            logger.info("Daily loss limit: $%.2f", daily_loss_limit)
            logger.info("=" * 70)

            loop_iteration = 0
            while True:
                try:
                    loop_iteration += 1
                    current_time = time.time()

                    # Clean up old signals (older than 60 seconds)
                    expired_keys = [
                        k for k, v in recent_signals.items() if current_time - v > 60
                    ]
                    for k in expired_keys:
                        del recent_signals[k]

                    # CHECK DAILY LOSS LIMIT
                    current_day = datetime.datetime.now().replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    if current_day > trading_day_start:
                        # New trading day - reset daily loss
                        trading_day_start = current_day
                        daily_loss = 0.0
                        logger.info("New trading day - daily loss reset to $0.00")

                    if daily_loss >= daily_loss_limit:
                        logger.error(
                            "Daily loss limit reached: $%.2f/$%.2f. Stopping all new trades.",
                            daily_loss,
                            daily_loss_limit,
                        )
                        # Don't generate new signals, but still monitor existing positions
                        all_signals = []
                    else:
                        # Calculate current daily P&L from all open positions
                        try:
                            cursor = db.conn.cursor()
                            cursor.execute(
                                """SELECT SUM(CASE 
                                WHEN trade_type = 'buy' THEN (close_price - open_price) * volume
                                WHEN trade_type = 'sell' THEN (open_price - close_price) * volume
                                ELSE 0 END) as daily_pl
                                FROM live_trades 
                                WHERE DATE(open_time) = DATE('now') AND close_time IS NOT NULL"""
                            )
                            result = cursor.fetchone()
                            daily_loss = -(result[0] if result[0] else 0.0)
                            if daily_loss > 0:
                                logger.debug("Current daily loss: $%.2f", daily_loss)
                        except Exception as e:
                            logger.debug(f"Could not calculate daily loss: {e}")

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

                    # Get account balance for position sizing
                    account_info = mt5.account_info()
                    account_balance = account_info.balance if account_info else 10000.0
                    logger.debug("Current account balance: $%.2f", account_balance)

                    # Collect signals from all trading pairs
                    all_signals = []
                    executed_trades = []
                    failed_trades = []

                    # Defensive check: ensure lists are never None
                    if all_signals is None:
                        all_signals = []

                    # Get position limits from config
                    max_positions = config.get("risk_management", {}).get(
                        "max_positions", 5
                    )
                    max_per_symbol = config.get("risk_management", {}).get(
                        "max_positions_per_symbol", 1
                    )

                    # Execute trades for each configured pair
                    if use_adaptive:
                        for symbol in pairs_to_trade:
                            signals = adaptive_trader.get_signals_adaptive(symbol)
                            if signals:
                                # Filter out duplicate signals within deduplication window
                                filtered_signals = []
                                for signal in signals:
                                    sig_key = f"{signal.get('symbol')}_{signal.get('action')}_{signal.get('timeframe', 'M15')}"
                                    if sig_key not in recent_signals:
                                        filtered_signals.append(signal)
                                        recent_signals[sig_key] = current_time
                                    else:
                                        logger.debug(
                                            "Skipped duplicate signal: %s (generated %d sec ago)",
                                            sig_key,
                                            int(current_time - recent_signals[sig_key]),
                                        )

                                all_signals.extend(filtered_signals)
                                # Execute each signal as a trade order
                                for signal in filtered_signals:
                                    try:
                                        strategy_name = signal.get(
                                            "strategy_info", {}
                                        ).get("name", "adaptive")

                                        signal_symbol = signal.get("symbol")

                                        # CHECK POSITION LIMITS BEFORE PLACING ORDER
                                        try:
                                            # Count current open positions (ANY status that isn't closed)
                                            cursor = db.conn.cursor()
                                            cursor.execute(
                                                "SELECT COUNT(*) as count FROM live_trades WHERE close_time IS NULL"
                                            )
                                            result = cursor.fetchone()
                                            total_open = result[0] if result else 0

                                            # Count open positions for this symbol
                                            cursor.execute(
                                                "SELECT COUNT(*) as count FROM live_trades t "
                                                "JOIN tradable_pairs tp ON t.symbol_id = tp.id "
                                                "WHERE tp.symbol = ? AND t.close_time IS NULL",
                                                (signal_symbol,),
                                            )
                                            result = cursor.fetchone()
                                            symbol_open = result[0] if result else 0

                                            # Enforce limits
                                            if total_open >= max_positions:
                                                logger.warning(
                                                    "Position limit reached: %d/%d total open positions. Skipping %s signal.",
                                                    total_open,
                                                    max_positions,
                                                    signal_symbol,
                                                )
                                                failed_trades.append(
                                                    {
                                                        "symbol": signal_symbol,
                                                        "action": signal.get("action"),
                                                        "strategy": strategy_name,
                                                        "reason": f"Max positions reached ({total_open}/{max_positions})",
                                                    }
                                                )
                                                continue

                                            if symbol_open >= max_per_symbol:
                                                logger.warning(
                                                    "Symbol position limit reached: %d/%d open for %s. Skipping signal.",
                                                    symbol_open,
                                                    max_per_symbol,
                                                    signal_symbol,
                                                )
                                                failed_trades.append(
                                                    {
                                                        "symbol": signal_symbol,
                                                        "action": signal.get("action"),
                                                        "strategy": strategy_name,
                                                        "reason": f"Max positions per symbol reached ({symbol_open}/{max_per_symbol})",
                                                    }
                                                )
                                                continue

                                        except Exception as e:
                                            logger.error(
                                                f"Failed to check position limits: {e}"
                                            )
                                            # Continue anyway but log the error
                                            pass

                                        # Calculate dynamic lot size based on confidence and account balance
                                        dynamic_lot_size = calculate_lot_size(
                                            signal, account_balance, config
                                        )
                                        signal["volume"] = dynamic_lot_size

                                        # Place the actual trade order
                                        if mt5_conn.place_order(signal, strategy_name):
                                            # Log executed trade directly to database
                                            symbol = signal.get("symbol")
                                            try:
                                                cursor = db.conn.cursor()
                                                cursor.execute(
                                                    "SELECT id FROM tradable_pairs WHERE symbol = ?",
                                                    (symbol,),
                                                )
                                                result = cursor.fetchone()
                                                if result:
                                                    symbol_id = result[0]
                                                    # Get current tick price for the symbol
                                                    tick = mt5.symbol_info_tick(symbol)
                                                    price = (
                                                        tick.ask
                                                        if signal.get("action") == "buy"
                                                        else tick.bid if tick else 0
                                                    )
                                                    # INSERT executed trade directly
                                                    cursor.execute(
                                                        """INSERT INTO live_trades 
                                                        (symbol_id, timeframe, strategy_name, trade_type, volume, 
                                                         open_price, status, open_time)
                                                        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                                                        (
                                                            symbol_id,
                                                            signal.get("timeframe"),
                                                            strategy_name,
                                                            signal.get(
                                                                "action", "unknown"
                                                            ),
                                                            dynamic_lot_size,
                                                            price,
                                                            "executed",
                                                        ),
                                                    )
                                                    db.conn.commit()
                                                    logger.debug(
                                                        f"Logged executed trade to database for {symbol}"
                                                    )
                                            except Exception as e:
                                                logger.error(
                                                    f"Failed to update trade status for {symbol}: {e}"
                                                )

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
                        # Fixed strategy mode: generate signals for ALL configured pairs
                        for symbol in pairs_to_trade:
                            signal = strategy_manager.generate_signals(
                                args.strategy, symbol=symbol
                            )
                            if signal:
                                logger.debug(
                                    "Fixed strategy %s generated %d signal(s) for %s",
                                    args.strategy,
                                    len(signal),
                                    symbol,
                                )
                                # Execute each signal as a trade order
                                for sig in signal:
                                    try:
                                        strategy_name = sig.get(
                                            "strategy_info", {}
                                        ).get("name", "fixed")
                                        signal_symbol = sig.get("symbol")

                                        # CHECK POSITION LIMITS BEFORE PLACING ORDER
                                        try:
                                            cursor = db.conn.cursor()
                                            cursor.execute(
                                                "SELECT COUNT(*) as count FROM live_trades WHERE close_time IS NULL"
                                            )
                                            result = cursor.fetchone()
                                            total_open = result[0] if result else 0

                                            cursor.execute(
                                                "SELECT COUNT(*) as count FROM live_trades t "
                                                "JOIN tradable_pairs tp ON t.symbol_id = tp.id "
                                                "WHERE tp.symbol = ? AND t.close_time IS NULL",
                                                (signal_symbol,),
                                            )
                                            result = cursor.fetchone()
                                            symbol_open = result[0] if result else 0

                                            if total_open >= max_positions:
                                                logger.warning(
                                                    "Position limit reached: %d/%d total. Skipping %s signal.",
                                                    total_open,
                                                    max_positions,
                                                    signal_symbol,
                                                )
                                                failed_trades.append(
                                                    {
                                                        "symbol": signal_symbol,
                                                        "action": sig.get("action"),
                                                        "strategy": strategy_name,
                                                        "reason": f"Max positions reached ({total_open}/{max_positions})",
                                                    }
                                                )
                                                continue

                                            if symbol_open >= max_per_symbol:
                                                logger.warning(
                                                    "Symbol position limit reached: %d/%d for %s.",
                                                    symbol_open,
                                                    max_per_symbol,
                                                    signal_symbol,
                                                )
                                                failed_trades.append(
                                                    {
                                                        "symbol": signal_symbol,
                                                        "action": sig.get("action"),
                                                        "strategy": strategy_name,
                                                        "reason": f"Max per symbol reached ({symbol_open}/{max_per_symbol})",
                                                    }
                                                )
                                                continue
                                        except Exception as e:
                                            logger.error(
                                                f"Failed to check position limits: {e}"
                                            )
                                            pass

                                        # Calculate dynamic lot size
                                        dynamic_lot_size = calculate_lot_size(
                                            sig, account_balance, config
                                        )
                                        sig["volume"] = dynamic_lot_size

                                        # Try to place the order
                                        if mt5_conn.place_order(sig, strategy_name):
                                            # LOG ONLY SUCCESSFUL TRADES
                                            symbol = sig.get("symbol")
                                            try:
                                                cursor = db.conn.cursor()
                                                cursor.execute(
                                                    "SELECT id FROM tradable_pairs WHERE symbol = ?",
                                                    (symbol,),
                                                )
                                                result = cursor.fetchone()
                                                if result:
                                                    symbol_id = result[0]
                                                    tick = mt5.symbol_info_tick(symbol)
                                                    price = (
                                                        (
                                                            tick.ask
                                                            if sig.get("action")
                                                            == "buy"
                                                            else tick.bid
                                                        )
                                                        if tick
                                                        else 0
                                                    )

                                                    cursor.execute(
                                                        """INSERT INTO live_trades 
                                                        (symbol_id, timeframe, strategy_name, trade_type, volume, 
                                                         open_price, status, open_time)
                                                        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                                                        (
                                                            symbol_id,
                                                            sig.get("timeframe"),
                                                            strategy_name,
                                                            sig.get(
                                                                "action", "unknown"
                                                            ),
                                                            dynamic_lot_size,
                                                            price,
                                                            "executed",
                                                        ),
                                                    )
                                                    db.conn.commit()
                                            except Exception as e:
                                                logger.error(
                                                    f"Failed to log trade: {e}"
                                                )

                                            executed_trades.append(
                                                {
                                                    "symbol": sig.get("symbol"),
                                                    "action": sig.get("action"),
                                                    "strategy": strategy_name,
                                                    "timeframe": sig.get("timeframe"),
                                                    "confidence": sig.get(
                                                        "confidence", 0
                                                    ),
                                                    "status": "executed",
                                                    "timestamp": time.time(),
                                                }
                                            )
                                            logger.info(
                                                f"[EXECUTED] {symbol} {sig.get('action').upper()} "
                                                f"(Strategy: {strategy_name})"
                                            )
                                        else:
                                            failed_trades.append(
                                                {
                                                    "symbol": sig.get("symbol"),
                                                    "action": sig.get("action"),
                                                    "strategy": strategy_name,
                                                    "reason": "MT5 order placement failed",
                                                }
                                            )
                                            logger.error(
                                                f"[FAILED] Trade placement failed: {sig.get('symbol')}"
                                            )
                                    except Exception as e:
                                        failed_trades.append(
                                            {
                                                "symbol": sig.get("symbol"),
                                                "action": sig.get("action"),
                                                "reason": str(e),
                                            }
                                        )
                                        logger.error(
                                            f"[FAILED] Exception placing trade: {e}"
                                        )
                            else:
                                logger.debug(
                                    f"Fixed strategy {args.strategy} generated no signals for {symbol}"
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

                    # MONITOR AND CLOSE POSITIONS (exit strategy)
                    try:
                        trade_monitor.monitor_positions(
                            strategy_name=args.strategy if not use_adaptive else None
                        )
                    except Exception as e:
                        logger.error(f"Error monitoring positions: {e}")

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
    """Execute GUI mode: Launch web dashboard.

    Args:
        config: Application configuration dictionary.
        args: Parsed command-line arguments.
        logger: Logger instance for output messages.
    """
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
    """Execute test mode: Run comprehensive test suite.

    Args:
        logger: Logger instance for output messages.
    """
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


if __name__ == "__main__":
    main()
