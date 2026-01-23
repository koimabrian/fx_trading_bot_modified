"""Backtesting framework for strategy validation and parameter optimization.

Manages data synchronization, multi-symbol backtesting, metrics calculation,
and result visualization with parameter optimization via backtesting.py.
"""

import argparse
import json
import logging
import os
import webbrowser
from datetime import datetime
from itertools import product

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from backtesting.lib import FractionalBacktest

from src.core.data_handler import DataHandler
from src.database.db_manager import DatabaseManager
from src.strategies.factory import StrategyFactory


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
        self.logger = logging.getLogger(__name__)

    def sync(self, symbol):
        """Sync data for backtesting from market_data to backtest_market_data table.
        Reads existing market_data and duplicates to backtest_market_data to avoid duplicates.
        """
        self.logger.info("Syncing backtest data for %s", symbol)

        for pair in self.config.get("pairs", []):
            if pair["symbol"] != symbol:
                continue

            tf = pair["timeframe"]
            tf_str = f"M{tf}" if tf < 60 else f"H{tf//60}"

            try:
                # Read from market_data (live data)
                query = "SELECT * FROM market_data WHERE symbol = ? AND timeframe = ? ORDER BY time ASC"
                data = pd.read_sql_query(query, self.db.conn, params=(symbol, tf_str))

                if data.empty:
                    self.logger.warning(
                        "No data in market_data for %s (%s). Run live sync first.",
                        symbol,
                        tf_str,
                    )
                    return

                # Check what's already in backtest_market_data to avoid duplicates
                try:
                    existing = pd.read_sql_query(
                        "SELECT time FROM backtest_market_data WHERE symbol = ? AND timeframe = ?",
                        self.db.conn,
                        params=(symbol, tf_str),
                    )
                    if not existing.empty:
                        data = data[~data["time"].isin(existing["time"])]
                        self.logger.debug(
                            "Skipped %d existing rows in backtest_market_data",
                            len(existing),
                        )
                except (pd.errors.DatabaseError, ValueError) as exc:
                    # backtest_market_data table may not exist yet
                    self.logger.debug(
                        "Exception checking existing backtest data: %s", exc
                    )

                if not data.empty:
                    data.to_sql(
                        "backtest_market_data",
                        self.db.conn,
                        if_exists="append",
                        index=False,
                    )
                    self.db.conn.commit()
                    self.logger.info(
                        "Synced %d rows to backtest_market_data for %s (%s)",
                        len(data),
                        symbol,
                        tf_str,
                    )
                else:
                    self.logger.info("No new rows to sync for %s (%s)", symbol, tf_str)
            except (IOError, ValueError) as exc:
                self.logger.error(
                    "Failed to sync backtest data for %s: %s", symbol, exc
                )

    def run_backtest(
        self, symbol, strategy_name, start_date=None, end_date=None, timeframe=None
    ):
        """Run backtest for specified symbol and strategy with parameter optimization

        Args:
            symbol: Trading symbol (e.g., 'BTCUSD')
            strategy_name: Name of strategy to backtest
            start_date: Optional start date (YYYY-MM-DD), falls back to config if not provided
            end_date: Optional end date (YYYY-MM-DD), falls back to config if not provided
            timeframe: Optional explicit timeframe (15 or 60), auto-detect if not provided
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
        else:  # MACD
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
            except (RuntimeError, ValueError, KeyError) as exc:
                self.logger.error("Backtest failed for params %s: %s", param_dict, exc)
                continue

        # Save results
        if best_stats is not None:
            # best_stats is a pandas Series - convert to dict for consistent access
            stats_dict = (
                best_stats.to_dict() if hasattr(best_stats, "to_dict") else best_stats
            )
            metrics = {
                "sharpe_ratio": stats_dict.get("Sharpe Ratio", 0),
                "sortino_ratio": stats_dict.get("Sortino Ratio", 0),
                "profit_factor": stats_dict.get("Profit Factor", 0),
                "calmar_ratio": stats_dict.get("Calmar Ratio", 0),
                "max_drawdown": stats_dict.get("Max. Drawdown [%]", 0),
                "return": stats_dict.get("Return [%]", 0),
                "ulcer_index": stats_dict.get("Ulcer Index", 0.0),
                "k_ratio": stats_dict.get("K-Ratio", 0.0),
                "tail_ratio": stats_dict.get("Tail Ratio", 0.0),
                "expectancy": stats_dict.get("Expectancy", 0.0),
                "roe": stats_dict.get("Return on Equity", 0.0),
                "time_to_recover": stats_dict.get("Time to Recover", 0.0),
            }
            try:
                # Ensure strategy exists in backtest_strategies table
                existing_strat = self.db.execute_query(
                    "SELECT id FROM backtest_strategies WHERE name = ? LIMIT 1",
                    (strategy_name.lower(),),
                )
                if existing_strat:
                    strategy_id = existing_strat[0]["id"]
                else:
                    # Insert strategy if it doesn't exist
                    self.db.execute_query(
                        "INSERT INTO backtest_strategies (name) VALUES (?)",
                        (strategy_name.lower(),),
                    )
                    result = self.db.execute_query(
                        "SELECT id FROM backtest_strategies WHERE name = ? LIMIT 1",
                        (strategy_name.lower(),),
                    )
                    strategy_id = result[0]["id"]

                self.db.execute_query(
                    "INSERT OR REPLACE INTO backtest_backtests (strategy_id, symbol, timeframe, metrics, timestamp) VALUES (?, ?, ?, ?, ?)",
                    (
                        strategy_id,
                        symbol,
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

                # Save optimal parameters
                param_values = (
                    symbol,
                    tf_str,
                    strategy_name,
                    best_params.get("period", best_params.get("fast_period", 0)),
                    best_params.get("overbought", best_params.get("slow_period", 0)),
                    best_params.get("oversold", best_params.get("signal_period", 0)),
                    float(stats_dict.get("Sharpe Ratio", 0)),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                self.db.execute_query(
                    "INSERT INTO optimal_params (symbol, timeframe, strategy_name, period, buy_threshold, sell_threshold, sharpe_ratio, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    param_values,
                )
            except (KeyError, TypeError, ValueError) as exc:
                self.logger.error("Failed to save backtest results: %s", exc)

            # Generate equity curve
            os.makedirs("backtests/results", exist_ok=True)
            equity_file = (
                f"backtests/results/equity_curve_{symbol}_{strategy_name}.html"
            )
            try:
                bt.plot(filename=equity_file)
                self.logger.info("Saved equity curve to %s", equity_file)
            except (IOError, OSError) as exc:
                self.logger.error("Failed to generate equity curve: %s", exc)

            # Generate optimization heatmap (for RSI only, as example)
            if strategy_name.lower() == "rsi":
                self.generate_heatmap(results, symbol, tf_str)

    def optimize(self, symbol, strategy_name, start_date=None, end_date=None):
        """Alias for run_backtest() - runs parameter optimization via backtest

        Args:
            symbol: Trading symbol
            strategy_name: Strategy name
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
        """
        self.logger.info(
            "Starting parameter optimization for %s on %s", strategy_name, symbol
        )
        self.run_backtest(symbol, strategy_name, start_date, end_date)

    def run_multi_backtest(
        self, symbols, strategy_name, start_date=None, end_date=None
    ):
        """Run backtests for multiple symbols & timeframes sequentially and compile results.

        Args:
            symbols: List of symbol strings (e.g., ['BTCUSD', 'ETHUSD', 'XRPUSD'])
            strategy_name: Name of strategy to backtest
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)

        Tests each symbol across all configured timeframes (M15 & H1).
        """
        if not symbols:
            self.logger.error("No symbols provided for multi-backtest")
            return

        # Get unique timeframes for each symbol from config
        symbol_timeframes = {}
        for pair in self.config.get("pairs", []):
            symbol = pair["symbol"]
            timeframe = pair["timeframe"]
            if symbol in symbols:
                if symbol not in symbol_timeframes:
                    symbol_timeframes[symbol] = []
                if timeframe not in symbol_timeframes[symbol]:
                    symbol_timeframes[symbol].append(timeframe)

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

        # Auto-open dashboard in browser
        dashboard_path = os.path.abspath("backtests/results/dashboard.html")
        if os.path.exists(dashboard_path):
            self.logger.info("Opening dashboard in browser: %s", dashboard_path)
            webbrowser.open(f"file:///{dashboard_path}")
        else:
            self.logger.warning("Dashboard file not found at %s", dashboard_path)

    def generate_multi_backtest_report(self, symbols, strategy_name):
        """Generate comparison report for multi-symbol backtests (all timeframes)"""
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
        except (KeyError, ValueError, IOError) as exc:
            self.logger.error("Failed to generate multi-backtest report: %s", exc)

    def generate_heatmap(self, results, symbol, timeframe):
        """Generate and save optimization heatmap for RSI parameters"""
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
        except (IOError, OSError, ValueError) as exc:
            self.logger.error("Failed to generate heatmap: %s", exc)

    def migrate(self):
        """Migrate database by dropping and recreating tables"""
        try:
            self.db.execute_query("DROP TABLE IF EXISTS backtest_market_data")
            self.db.execute_query("DROP TABLE IF EXISTS backtest_strategies")
            self.db.execute_query("DROP TABLE IF EXISTS backtest_backtests")
            self.db.execute_query("DROP TABLE IF EXISTS optimal_params")
            self.db.create_tables()
            self.logger.info("Database migration completed successfully")
        except (OSError, TypeError) as exc:
            self.logger.error("Database migration failed: %s", exc)

    def run(self):
        """Parse arguments and run the specified mode"""
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
                # Extract all unique symbols from config pairs
                symbols = sorted(set(p["symbol"] for p in self.config.get("pairs", [])))
                if not symbols:
                    self.logger.error("No pairs found in config")
                    return
            self.run_multi_backtest(
                symbols, args.strategy, args.start_date, args.end_date
            )
        elif args.mode == "migrate":
            self.migrate()
        elif args.mode == "run":
            # Legacy mode: runs backtest if strategy provided, otherwise sync
            if args.strategy:
                self.run_backtest(
                    args.symbol, args.strategy, args.start_date, args.end_date
                )
            else:
                self.sync(args.symbol)


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
    for category, data in categories.items():
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
    from src.utils.logger import setup_logging

    setup_logging()
    with open("src/config/config.yaml", "r", encoding="utf-8") as file:
        config_data = yaml.safe_load(file)

    # Auto-generate pairs from pair_config if not already populated
    generate_pairs_from_config(config_data)

    BacktestManager(config_data).run()
