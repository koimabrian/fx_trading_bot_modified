"""Backtesting framework for strategy validation and parameter optimization.

Manages data synchronization, multi-symbol backtesting, metrics calculation,
and result visualization with parameter optimization via backtesting.py.
"""

import argparse
import json
import math
import os
from datetime import datetime
from itertools import product

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tqdm import tqdm

from backtesting.lib import FractionalBacktest
from src.backtesting.trade_extractor import TradeExtractor
from src.core.data_handler import DataHandler
from src.database.db_manager import DatabaseManager
from src.strategies.factory import StrategyFactory
from src.utils.error_handler import ErrorHandler
from src.utils.logging_factory import LoggingFactory


class BacktestManager:
    """Manages backtesting operations including data sync, execution, and visualization."""

    def __init__(self, config_dict):
        """Initialize BacktestManager with configuration.

        Args:
            config_dict: Configuration dictionary with database and backtesting settings
        """
        self.config = config_dict
        self.db = DatabaseManager(config_dict["database"])
        self.db.connect()
        self.db.create_tables()
        self.logger = LoggingFactory.get_logger(__name__)

    def _sanitize_value(self, value):
        """Convert NaN and inf values to 0 for JSON serialization.

        backtesting.py may return NaN or inf values which are not valid JSON.
        This ensures all metrics can be serialized to JSON.

        Args:
            value: Numeric value that may be NaN, inf, or None.

        Returns:
            Sanitized float value, with NaN/inf/None converted to 0.
        """
        # Handle None
        if value is None:
            return 0

        # Handle NaN (from NumPy or math)
        try:
            if math.isnan(value) or (isinstance(value, float) and np.isnan(value)):
                return 0
        except (TypeError, ValueError):
            pass

        # Handle inf
        try:
            if math.isinf(value):
                return 0
        except (TypeError, ValueError):
            pass

        # Return as-is if valid
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0

    def run_backtest(
        self,
        symbol=None,
        strategy_name=None,
        start_date=None,
        end_date=None,
        timeframe=None,
    ):
        """Run backtest for specified symbol and strategy with parameter optimization.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSD'), if None backtest all.
            strategy_name: Name of strategy to backtest, if None backtest all.
            start_date: Optional start date (YYYY-MM-DD), falls back to config.
            end_date: Optional end date (YYYY-MM-DD), falls back to config.
            timeframe: Optional explicit timeframe (15 or 60), auto-detect if not provided.

        Returns:
            None. Results are saved to database and logged.
        """
        # If no strategy specified, backtest all configured strategies
        if strategy_name is None:
            strategies_to_test = self.config.get(
                "strategies", [{"name": "rsi"}, {"name": "macd"}]
            )
        else:
            strategies_to_test = [
                s
                for s in self.config.get("strategies", [])
                if s["name"].lower() == strategy_name.lower()
            ]
            if not strategies_to_test:
                self.logger.error("Strategy %s not found in config", strategy_name)
                return

        # If no symbol specified, get all symbols from database
        if symbol is None:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT DISTINCT symbol FROM tradable_pairs")
            symbols_to_test = [row[0] for row in cursor.fetchall()]
            if not symbols_to_test:
                self.logger.warning("No symbols found in tradable_pairs table")
                return
        else:
            symbols_to_test = [symbol]

        # Get all timeframes from config
        timeframes_to_test = self.config.get("timeframes", [15, 60, 240])

        # Calculate total tests for progress bar
        total_tests = len(symbols_to_test) * len(strategies_to_test)
        if timeframe is None:
            total_tests *= len(timeframes_to_test)

        # Create progress bar
        progress_bar = tqdm(total=total_tests, desc="Backtesting", unit="test")

        # Run backtest for each combination
        for sym in symbols_to_test:
            for strategy_config in strategies_to_test:
                # If specific timeframe provided, use it; otherwise test all timeframes
                if timeframe:
                    self._run_single_backtest(
                        sym, strategy_config["name"], start_date, end_date, timeframe
                    )
                    progress_bar.update(1)
                else:
                    for tf in timeframes_to_test:
                        self._run_single_backtest(
                            sym, strategy_config["name"], start_date, end_date, tf
                        )
                        progress_bar.update(1)

        progress_bar.close()

    def _run_single_backtest(
        self, symbol, strategy_name, start_date=None, end_date=None, timeframe=None
    ):
        """Run backtest for a single symbol/strategy combination.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSD').
            strategy_name: Name of strategy to backtest.
            start_date: Optional start date.
            end_date: Optional end date.
            timeframe: Optional explicit timeframe.

        Returns:
            None. Results are saved to database.
        """
        strategy_config = next(
            (
                s
                for s in self.config["strategies"]
                if s["name"].lower() == strategy_name.lower()
            ),
            None,
        )
        if not strategy_config:
            self.logger.error("Strategy %s not found in config", strategy_name)
            return

        # Get date range from args or config
        if not start_date or not end_date:
            data_range = self.config.get("backtesting", {}).get(
                "data_range", "2024-01-01:2025-12-31"
            )
            if ":" in data_range:
                config_start, config_end = data_range.split(":")
            else:
                config_start = config_end = "2024-01-01"

            start_date = start_date or config_start.strip()
            end_date = end_date or config_end.strip()

        # Use explicit timeframe if provided, otherwise get first matching from config
        if timeframe is None:
            tf = next(
                (p["timeframe"] for p in self.config["pairs"] if p["symbol"] == symbol),
                15,
            )
        else:
            tf = timeframe

        tf_str = f"M{tf}" if tf < 60 else f"H{tf//60}"

        self.logger.info("=" * 80)
        self.logger.info(
            "[BACKTEST] Strategy: %s | Pair: %s | Timeframe: %s [%s]",
            strategy_name.upper(),
            symbol,
            tf_str,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        self.logger.info("=" * 80)
        self.logger.info(
            "Running backtest for %s (%s) from %s to %s",
            symbol,
            strategy_name,
            start_date,
            end_date,
        )

        # Fetch backtest data
        data_handler = DataHandler(self.db, self.config)
        data = data_handler.prepare_backtest_data(symbol, tf_str)
        if data is None or data.empty:
            self.logger.error("No data available for %s (%s)", symbol, tf_str)
            return

        # Filter data by date range (no weekend restrictions for historical backtest)
        # Data has Datetime as index from prepare_backtest_data()
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        data = data[(data.index >= start_dt) & (data.index <= end_dt)]

        if data.empty:
            self.logger.error(
                "No data in range %s to %s for %s (%s)",
                start_date,
                end_date,
                symbol,
                tf_str,
            )
            return

        self.logger.info(
            "Backtest data: %d rows from %s to %s",
            len(data),
            data.index[0],
            data.index[-1],
        )

        # Get strategy class
        strategy_class = StrategyFactory.create_strategy(
            strategy_name,
            strategy_config["params"],
            self.db,
            mode="backtest",
            config=self.config,
        ).backtest_strategy

        # Optimization parameters
        opt_params = (
            self.config.get("backtesting", {})
            .get("optimization", {})
            .get(strategy_name.lower(), {})
        )
        if strategy_name.lower() == "rsi":
            param_combinations = list(
                product(
                    opt_params.get(
                        "period", [strategy_config["params"].get("period", 14)]
                    ),
                    opt_params.get(
                        "overbought", [strategy_config["params"].get("overbought", 70)]
                    ),
                    opt_params.get(
                        "oversold", [strategy_config["params"].get("oversold", 30)]
                    ),
                )
            )
            param_keys = ["period", "overbought", "oversold"]
        elif strategy_name.lower() == "macd":
            param_combinations = list(
                product(
                    opt_params.get(
                        "fast_period",
                        [strategy_config["params"].get("fast_period", 12)],
                    ),
                    opt_params.get(
                        "slow_period",
                        [strategy_config["params"].get("slow_period", 26)],
                    ),
                    opt_params.get(
                        "signal_period",
                        [strategy_config["params"].get("signal_period", 9)],
                    ),
                )
            )
            param_keys = ["fast_period", "slow_period", "signal_period"]
        else:  # SMA, EMA - only fast_period and slow_period
            param_combinations = list(
                product(
                    opt_params.get(
                        "fast_period",
                        [strategy_config["params"].get("fast_period", 10)],
                    ),
                    opt_params.get(
                        "slow_period",
                        [strategy_config["params"].get("slow_period", 20)],
                    ),
                )
            )
            param_keys = ["fast_period", "slow_period"]

        # Run backtests with optimization
        best_stats = None
        best_params = None
        results = []
        for params in param_combinations:
            param_dict = dict(zip(param_keys, params))
            param_dict["volume"] = strategy_config["params"].get("volume", 0.01)
            # Use FractionalBacktest to avoid margin warnings with fractional crypto amounts
            bt = FractionalBacktest(
                data,
                strategy_class,
                cash=100000,
                commission=0.001,
                exclusive_orders=True,
                finalize_trades=True,
            )
            try:
                stats = bt.run(**param_dict)
                results.append((param_dict, stats))
                if best_stats is None or stats.get("Sharpe Ratio", 0) > best_stats.get(
                    "Sharpe Ratio", 0
                ):
                    best_stats = stats
                    best_params = param_dict
            except Exception as exc:
                ErrorHandler.handle_error(exc, context="backtest_run")
                continue

        # Save results
        if best_stats is not None:
            # best_stats is a pandas Series - convert to dict for consistent access
            stats_dict = (
                best_stats.to_dict() if hasattr(best_stats, "to_dict") else best_stats
            )
            metrics = {
                "sharpe_ratio": self._sanitize_value(stats_dict.get("Sharpe Ratio", 0)),
                "sortino_ratio": self._sanitize_value(
                    stats_dict.get("Sortino Ratio", 0)
                ),
                "profit_factor": self._sanitize_value(
                    stats_dict.get("Profit Factor", 0)
                ),
                "calmar_ratio": self._sanitize_value(stats_dict.get("Calmar Ratio", 0)),
                "max_drawdown": self._sanitize_value(
                    stats_dict.get("Max. Drawdown [%]", 0)
                ),
                "return": self._sanitize_value(stats_dict.get("Return [%]", 0)),
                "ulcer_index": self._sanitize_value(stats_dict.get("Ulcer Index", 0.0)),
                "k_ratio": self._sanitize_value(stats_dict.get("K-Ratio", 0.0)),
                "tail_ratio": self._sanitize_value(stats_dict.get("Tail Ratio", 0.0)),
                "expectancy": self._sanitize_value(stats_dict.get("Expectancy", 0.0)),
                "roe": self._sanitize_value(stats_dict.get("Return on Equity", 0.0)),
                "time_to_recover": self._sanitize_value(
                    stats_dict.get("Time to Recover", 0.0)
                ),
            }
            try:
                # Ensure strategy exists in backtest_strategies table
                existing_strat = self.db.execute_query(
                    "SELECT id FROM backtest_strategies WHERE name = ? LIMIT 1",
                    (strategy_name.lower(),),
                ).fetchall()
                if existing_strat:
                    strategy_id = existing_strat[0][0]
                else:
                    # Insert strategy if it doesn't exist
                    self.db.execute_query(
                        "INSERT INTO backtest_strategies (name) VALUES (?)",
                        (strategy_name.lower(),),
                    )
                    result = self.db.execute_query(
                        "SELECT id FROM backtest_strategies WHERE name = ? LIMIT 1",
                        (strategy_name.lower(),),
                    ).fetchall()
                    strategy_id = result[0][0]

                # Get symbol_id from tradable_pairs
                symbol_id_result = self.db.execute_query(
                    "SELECT id FROM tradable_pairs WHERE symbol = ?",
                    (symbol,),
                ).fetchall()
                if not symbol_id_result:
                    self.logger.error("Symbol %s not found in tradable_pairs", symbol)
                    return
                symbol_id = symbol_id_result[0][0]

                # Calculate rank_score from metrics
                sharpe = metrics.get("sharpe_ratio", 0)
                profit_factor = metrics.get("profit_factor", 0)
                max_dd = (
                    abs(metrics.get("max_drawdown", 0))
                    if metrics.get("max_drawdown")
                    else 0
                )

                # Simple rank score: higher sharpe, higher profit factor, lower drawdown
                rank_score = (
                    (sharpe / 10.0 if sharpe != 0 else 0)
                    + (min(profit_factor / 5.0, 1.0) if profit_factor != 0 else 0)
                    - (max_dd * 10 if max_dd != 0 else 0)
                )
                rank_score = max(0, min(1.0, rank_score))  # Clamp to 0-1
                metrics["rank_score"] = rank_score

                self.db.execute_query(
                    "INSERT OR REPLACE INTO backtest_backtests (strategy_id, symbol_id, timeframe, metrics, timestamp) VALUES (?, ?, ?, ?, ?)",
                    (
                        strategy_id,
                        symbol_id,
                        tf_str,
                        json.dumps(metrics),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                self.logger.info(
                    "Backtest completed for %s with %s: %s",
                    symbol,
                    strategy_name,
                    metrics,
                )

                # Save optimal parameters (update to use symbol_id)
                param_values = (
                    symbol_id,
                    tf_str,
                    strategy_name,
                    json.dumps(best_params),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                self.db.execute_query(
                    "INSERT OR REPLACE INTO optimal_parameters (symbol_id, timeframe, strategy_name, parameter_value, last_optimized) VALUES (?, ?, ?, ?, ?)",
                    param_values,
                )

                # Extract and store individual trades from backtest results
                self._extract_and_store_trades(
                    best_stats, symbol_id, strategy_id, tf_str, best_params
                )

            except Exception as exc:
                ErrorHandler.handle_error(exc, context="save_backtest_results")

            # Note: Equity curve plotting removed per user request - only terminal progress required
            # Files would be saved to: backtests/results/equity_curve_{symbol}_{strategy_name}.html
            # View results in web dashboard instead: http://127.0.0.1:5000/backtest

            # Generate optimization heatmap (for RSI only, as example)
            # Note: Heatmap generation removed per user request - only terminal progress required

    def optimize(self, symbol, strategy_name, start_date=None, end_date=None):
        """Alias for run_backtest() - runs parameter optimization via backtest.

        Args:
            symbol: Trading symbol.
            strategy_name: Strategy name.
            start_date: Optional start date (YYYY-MM-DD).
            end_date: Optional end date (YYYY-MM-DD).

        Returns:
            None. Results are saved to database.
        """
        self.logger.info(
            "Starting parameter optimization for %s on %s", strategy_name, symbol
        )
        self.run_backtest(symbol, strategy_name, start_date, end_date)

    def run_multi_backtest(
        self, symbols, strategy_name, start_date=None, end_date=None
    ):
        """Run backtests for multiple symbols & timeframes sequentially.

        Args:
            symbols: List of symbol strings (e.g., ['BTCUSD', 'ETHUSD', 'XRPUSD']).
            strategy_name: Name of strategy to backtest.
            start_date: Optional start date (YYYY-MM-DD).
            end_date: Optional end date (YYYY-MM-DD).

        Returns:
            None. Tests each symbol across all configured timeframes (M15 & H1)
            and saves results to database.
        """
        if not symbols:
            self.logger.error("No symbols provided for multi-backtest")
            return

        # Get unique timeframes from config
        timeframes = self.config.get("timeframes", [15, 60, 240])

        # Create symbol_timeframes mapping using all symbols with all timeframes
        symbol_timeframes = {}
        for symbol in symbols:
            symbol_timeframes[symbol] = timeframes

        total_tests = sum(len(tfs) for tfs in symbol_timeframes.values())
        self.logger.info(
            "Starting multi-backtest for %d symbols across %d timeframes with strategy %s",
            len(symbols),
            total_tests,
            strategy_name,
        )

        all_results = {}
        test_count = 0
        for symbol in symbols:
            timeframes = symbol_timeframes.get(symbol, [])
            if not timeframes:
                self.logger.warning("No configured timeframes found for %s", symbol)
                continue

            for timeframe in sorted(timeframes):
                tf_str = f"M{timeframe}" if timeframe < 60 else f"H{timeframe//60}"
                self.logger.info(
                    "Backtesting %s (%s) [%d/%d]...",
                    symbol,
                    tf_str,
                    test_count + 1,
                    total_tests,
                )
                self.run_backtest(
                    symbol, strategy_name, start_date, end_date, timeframe=timeframe
                )
                all_results[f"{symbol}_{tf_str}"] = True
                test_count += 1

        self.logger.info(
            "Multi-backtest completed: %d tests across %d symbols",
            test_count,
            len(symbols),
        )
        self.generate_multi_backtest_report(symbols, strategy_name)

        # Print completion message with dashboard info
        self.logger.info("=" * 80)
        self.logger.info("[COMPLETE] BACKTEST SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(
            "Backtest Results: backtests/results/multi_backtest_%s_report.csv",
            strategy_name,
        )
        self.logger.info("Optimal Parameters: See optimal_parameters table in database")
        self.logger.info("")
        self.logger.info("[INFO] TO VIEW RESULTS:")
        self.logger.info("  1. Backtest Dashboard: python -m src.main --mode gui")
        self.logger.info("     Navigate to: http://127.0.0.1:5000/backtest")
        self.logger.info("  2. Live Trading Dashboard: python -m src.main --mode live")
        self.logger.info("     Navigate to: http://127.0.0.1:5000")
        self.logger.info("=" * 80)

    def generate_multi_backtest_report(self, symbols, strategy_name):
        """Generate comparison report for multi-symbol backtests.

        Args:
            symbols: List of symbol strings to include in report.
            strategy_name: Name of strategy to report on.

        Returns:
            None. Report saved to backtests/results/ directory.
        """
        try:
            # Get all results for each symbol & timeframe combination
            all_metrics = []
            for symbol in symbols:
                query = """
                    SELECT symbol, timeframe, metrics, timestamp 
                    FROM backtest_backtests b
                    JOIN backtest_strategies s ON b.strategy_id = s.id
                    WHERE s.name = ? AND b.symbol = ?
                    ORDER BY b.timestamp DESC
                """
                results = self.db.execute_query(query, (strategy_name.lower(), symbol))

                # Get most recent result for each timeframe
                seen_timeframes = set()
                for result in results:
                    tf = result["timeframe"]
                    if tf not in seen_timeframes:
                        metrics = json.loads(result["metrics"])
                        all_metrics.append(
                            {
                                "symbol": symbol,
                                "timeframe": tf,
                                **metrics,
                            }
                        )
                        seen_timeframes.add(tf)

            # Create comparison dataframe
            if all_metrics:
                df = pd.DataFrame(all_metrics)
                report_file = (
                    f"backtests/results/multi_backtest_{strategy_name}_report.csv"
                )
                os.makedirs("backtests/results", exist_ok=True)
                df.to_csv(report_file, index=False)
                self.logger.info("Saved multi-backtest report to %s", report_file)

                # Log summary
                self.logger.info("\n%s", "=" * 80)
                self.logger.info("MULTI-BACKTEST SUMMARY: %s", strategy_name)
                self.logger.info("=" * 80)
                self.logger.info(df.to_string())
                self.logger.info("=" * 80)
        except Exception as exc:
            ErrorHandler.handle_error(exc, context="generate_multi_backtest_report")

    def generate_heatmap(self, results, symbol, timeframe):
        """Generate and save optimization heatmap for RSI parameters.

        Args:
            results: List of (params, stats) tuples from optimization.
            symbol: Trading symbol for title.
            timeframe: Timeframe string for title.

        Returns:
            None. Heatmap saved to backtests/results/ directory.
        """
        try:
            periods = sorted(set(p["period"] for p, _ in results))
            oversolds = sorted(set(p["oversold"] for p, _ in results))
            heatmap_data = np.zeros((len(oversolds), len(periods)))
            for i, oversold in enumerate(oversolds):
                for j, period in enumerate(periods):
                    for params, stats in results:
                        if (
                            params["period"] == period
                            and params["oversold"] == oversold
                        ):
                            heatmap_data[i, j] = stats["Sharpe Ratio"]

            plt.figure(figsize=(10, 8))
            plt.imshow(heatmap_data, cmap="viridis", interpolation="nearest")
            plt.colorbar(label="Sharpe Ratio")
            plt.xticks(np.arange(len(periods)), periods)
            plt.yticks(np.arange(len(oversolds)), oversolds)
            plt.xlabel("RSI Period")
            plt.ylabel("Oversold Threshold")
            plt.title(f"RSI Optimization Heatmap - {symbol} ({timeframe})")
            heatmap_file = (
                f"backtests/results/rsi_optimization_heatmap_{symbol}_{timeframe}.html"
            )
            plt.savefig(heatmap_file.replace(".html", ".png"))
            plt.close()
            self.logger.info(
                "Saved heatmap to %s", heatmap_file.replace(".html", ".png")
            )
        except Exception as exc:
            ErrorHandler.handle_error(exc, context="generate_heatmap")

    def run(self):
        """Parse arguments and run the specified mode.

        Returns:
            None. Executes the requested backtest mode.
        """
        parser = argparse.ArgumentParser(description="FX Trading Bot Backtest Manager")
        parser.add_argument(
            "--mode",
            choices=[
                "sync",
                "backtest",
                "optimize",
                "multi-backtest",
                "migrate",
                "run",
            ],
            required=True,
            help="Mode: sync (copy market_data to backtest_market_data), backtest (run single backtest), optimize (parameter optimization), multi-backtest (backtest multiple pairs), migrate (reset DB), run (legacy backtest)",
        )
        parser.add_argument(
            "--symbol",
            default=None,
            help="Trading pair symbol (e.g., BTCUSD, XAUUSD) - use comma-separated for multi-backtest. If not specified, uses all pairs from config",
        )
        parser.add_argument(
            "--strategy", default=None, help="Strategy name (e.g., rsi, macd)"
        )
        parser.add_argument(
            "--start-date",
            default=None,
            help="Backtest start date (YYYY-MM-DD format). Falls back to config if not provided.",
        )
        parser.add_argument(
            "--end-date",
            default=None,
            help="Backtest end date (YYYY-MM-DD format). Falls back to config if not provided.",
        )
        args = parser.parse_args()

        if args.mode == "sync":
            self.sync(args.symbol)
        elif args.mode == "backtest":
            if not args.strategy:
                self.logger.error("--strategy is required for backtest mode")
                return
            self.run_backtest(
                args.symbol, args.strategy, args.start_date, args.end_date
            )
        elif args.mode == "optimize":
            if not args.strategy:
                self.logger.error("--strategy is required for optimize mode")
                return
            self.optimize(args.symbol, args.strategy, args.start_date, args.end_date)
        elif args.mode == "multi-backtest":
            if not args.strategy:
                self.logger.error("--strategy is required for multi-backtest mode")
                return
            # Parse comma-separated symbols or extract all from config
            if args.symbol:
                symbols = [s.strip().upper() for s in args.symbol.split(",")]
            else:
                # Extract all unique symbols from database
                cursor = self.db.conn.cursor()
                cursor.execute(
                    "SELECT DISTINCT symbol FROM tradable_pairs ORDER BY symbol"
                )
                symbols = [row[0] for row in cursor.fetchall()]
                if not symbols:
                    self.logger.error("No symbols found in database")
                    return
            self.run_multi_backtest(
                symbols, args.strategy, args.start_date, args.end_date
            )
        elif args.mode == "run":
            # Legacy mode: runs backtest if strategy provided, otherwise sync
            if args.strategy:
                self.run_backtest(
                    args.symbol, args.strategy, args.start_date, args.end_date
                )
            else:
                self.sync(args.symbol)

    def _extract_and_store_trades(
        self, stats, symbol_id, strategy_id, timeframe, params
    ):
        """Extract individual trades from backtest stats and store in database.

        Args:
            stats: Stats object from backtesting.py
            symbol_id: ID of symbol in tradable_pairs table
            strategy_id: ID of strategy in backtest_strategies table
            timeframe: Timeframe string (e.g., 'M15', 'H1')
            params: Parameters used for the backtest
        """
        try:
            # Extract trades using TradeExtractor
            trades_df = TradeExtractor.extract_trades(stats)
            if trades_df is None or trades_df.empty:
                self.logger.debug("No trades found in backtest results")
                return

            # Calculate trade statistics
            trade_stats = TradeExtractor.calculate_trade_statistics(trades_df)

            # Store each trade in database
            for _, trade in trades_df.iterrows():
                try:
                    self.db.execute_query(
                        """INSERT OR REPLACE INTO backtest_trades 
                           (strategy_id, symbol_id, timeframe, entry_time, exit_time, 
                            entry_price, exit_price, size, pnl, pnl_pct, duration_hours, 
                            params, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            strategy_id,
                            symbol_id,
                            timeframe,
                            str(trade["entry_time"]),
                            str(trade["exit_time"]),
                            float(trade["entry_price"]),
                            float(trade["exit_price"]),
                            float(trade["size"]),
                            float(trade["pnl"]),
                            float(trade["pnl_pct"]),
                            float(trade["duration_hours"]),
                            json.dumps(params),
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ),
                    )
                except (KeyError, TypeError, ValueError) as e:
                    self.logger.warning(
                        f"Failed to store trade for {symbol_id}/{strategy_id}: {e}"
                    )
                    continue

            self.logger.info(
                f"Stored {len(trades_df)} trades for strategy {strategy_id}, "
                f"symbol {symbol_id}, timeframe {timeframe}"
            )

            # Log trade statistics summary
            self.logger.info(
                f"Trade Statistics: {trade_stats['total_trades']} total, "
                f"{trade_stats['winning_trades']} wins ({trade_stats['win_rate']:.1f}%), "
                f"Profit Factor: {trade_stats['profit_factor']:.2f}"
            )

        except Exception as e:
            ErrorHandler.handle_error(e, context="extract_and_store_trades")


if __name__ == "__main__":
    from src.utils.config_manager import ConfigManager
    from src.utils.logging_factory import LoggingFactory

    LoggingFactory.configure()
    config_data = ConfigManager.get_config()

    BacktestManager(config_data).run()
