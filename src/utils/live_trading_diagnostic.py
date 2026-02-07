"""Comprehensive diagnostics for live trading execution.

Validates configuration, data availability, MT5 connection, signal generation,
and trade execution to identify blockers preventing trades from executing.
"""

from typing import Dict, List, Optional, Tuple

from src.core.adaptive_trader import AdaptiveTrader
from src.database.db_manager import DatabaseManager
from src.mt5_connector import MT5Connector
from src.strategy_manager import StrategyManager
from src.utils.backtesting_utils import volatility_rank_pairs


class LiveTradingDiagnostic:
    """Comprehensive diagnostics for live trading issues."""

    def __init__(self, config: Dict, db: DatabaseManager, mt5_conn: MT5Connector):
        """Initialize diagnostic system.

        Args:
            config: Configuration dictionary
            db: Database manager instance
            mt5_conn: MT5 connector instance
        """
        self.config = config
        self.db = db
        self.mt5_conn = mt5_conn
        from src.utils.logging_factory import LoggingFactory
        self.logger = LoggingFactory.get_logger(__name__)
        self.issues = []
        self.warnings = []
        self.info = []

    def run_full_diagnostic(self) -> Dict:
        """Run comprehensive diagnostic checks.

        Returns:
            Dictionary with diagnostic results including issues, warnings, info
        """
        self.logger.info("=" * 70)
        self.logger.info("LIVE TRADING DIAGNOSTIC - COMPREHENSIVE CHECK")
        self.logger.info("=" * 70)

        self.issues = []
        self.warnings = []
        self.info = []

        # Run all checks
        self.check_mt5_connection()
        self.check_database_setup()
        self.check_tradable_pairs()
        self.check_market_data()
        self.check_strategies_configured()
        self.check_optimal_parameters()
        self.check_trading_rules()
        self.check_signal_generation()
        self.check_volatility_ranking()

        # Generate report
        report = {
            "status": "OK" if not self.issues else "ERROR",
            "issues": self.issues,
            "warnings": self.warnings,
            "info": self.info,
            "can_trade": len(self.issues) == 0,
        }

        self._print_report(report)
        return report

    def check_mt5_connection(self):
        """Verify MT5 connection is active."""
        self.logger.info("\n[1/9] Checking MT5 Connection...")
        try:
            # Try to get symbol list - this verifies connection is working
            import MetaTrader5 as mt5

            if mt5.symbols_total() > 0:
                self.info.append("MT5 Connected - Ready to trade")
            else:
                self.warnings.append("MT5 may not be connected - no symbols available")
        except Exception as e:
            self.issues.append(f"MT5 connection error: {e}")

    def check_database_setup(self):
        """Verify database tables exist and are properly configured."""
        self.logger.info("[2/9] Checking Database Setup...")
        try:
            # Check essential tables
            tables_to_check = [
                "tradable_pairs",
                "market_data",
                "optimal_parameters",
                "backtest_backtests",
                "trades",
            ]

            for table in tables_to_check:
                cursor = self.db.conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                )
                if not cursor.fetchone():
                    self.issues.append(f"Database table missing: {table}")
                else:
                    self.info.append(f"[OK] Table exists: {table}")

        except Exception as e:
            self.issues.append(f"Database check error: {e}")

    def check_tradable_pairs(self):
        """Verify tradable pairs are populated in database."""
        self.logger.info("[3/9] Checking Tradable Pairs...")
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tradable_pairs")
            pair_count = cursor.fetchone()[0]

            if pair_count == 0:
                self.issues.append(
                    "No pairs in tradable_pairs table - run 'init' mode first"
                )
                return

            sample_pairs = self.db.get_symbol_sample(limit=5)
            self.info.append(
                f"Found {pair_count} tradable pairs (e.g., {', '.join(sample_pairs)})"
            )

        except Exception as e:
            self.issues.append(f"Tradable pairs check error: {e}")

    def check_market_data(self):
        """Verify market data availability for trading."""
        self.logger.info("[4/9] Checking Market Data...")
        try:
            cursor = self.db.conn.cursor()

            # Check total data rows
            cursor.execute("SELECT COUNT(*) FROM market_data")
            data_count = cursor.fetchone()[0]

            if data_count == 0:
                self.issues.append("No market data in database - run 'sync' mode first")
                return

            # Check recent data
            cursor.execute(
                "SELECT COUNT(*) FROM market_data WHERE time > datetime('now', '-1 hour')"
            )
            recent_count = cursor.fetchone()[0]

            # Check data per pair
            cursor.execute(
                """
                SELECT symbol, COUNT(*) as count 
                FROM market_data 
                GROUP BY symbol 
                ORDER BY count DESC 
                LIMIT 3
            """
            )
            top_pairs = cursor.fetchall()

            self.info.append(f"Total market data rows: {data_count}")
            if recent_count > 0:
                self.info.append(f"Recent data (last 1h): {recent_count} rows")
            else:
                self.warnings.append("No data from last hour - consider running sync")

            if top_pairs:
                pair_info = ", ".join([f"{p[0]}({p[1]})" for p in top_pairs])
                self.info.append(f"Top pairs by data: {pair_info}")

        except Exception as e:
            self.issues.append(f"Market data check error: {e}")

    def check_strategies_configured(self):
        """Verify strategies are properly configured."""
        self.logger.info("[5/9] Checking Strategies Configuration...")
        try:
            strategies = self.config.get("strategies", [])

            if not strategies:
                self.issues.append("No strategies configured in config.yaml")
                return

            strategy_names = [s.get("name", "unknown") for s in strategies]
            self.info.append(f"Configured strategies: {', '.join(strategy_names)}")

            # Check strategy parameters
            for strategy in strategies:
                name = strategy.get("name", "unknown")
                params = strategy.get("params", {})
                if not params:
                    self.warnings.append(f"Strategy '{name}' has no parameters defined")
                else:
                    self.info.append(f"  [OK] {name}: {len(params)} parameters")

        except Exception as e:
            self.issues.append(f"Strategy configuration error: {e}")

    def check_optimal_parameters(self):
        """Verify optimal parameters are available for strategies."""
        self.logger.info("[6/9] Checking Optimal Parameters...")
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM optimal_parameters")
            param_count = cursor.fetchone()[0]

            if param_count == 0:
                self.warnings.append(
                    "No optimal parameters found - run 'backtest' mode first"
                )
                return

            # Check params per strategy
            cursor.execute(
                """
                SELECT strategy_name, COUNT(*) as count 
                FROM optimal_parameters 
                GROUP BY strategy_name
            """
            )
            strategy_params = cursor.fetchall()

            self.info.append(f"Total optimal parameters: {param_count}")
            for strat, count in strategy_params:
                self.info.append(f"  {strat}: {count} parameter sets")

        except Exception as e:
            self.issues.append(f"Optimal parameters check error: {e}")

    def check_trading_rules(self):
        """Verify trading rules configuration."""
        self.logger.info("[7/9] Checking Trading Rules...")
        try:
            risk_config = self.config.get("risk_management", {})

            if not risk_config:
                self.warnings.append("No risk management rules configured")
                return

            max_pos = risk_config.get("max_positions", 10)
            lot_size = risk_config.get("lot_size", 0.01)
            sl = risk_config.get("stop_loss_percent", 1.0)
            tp = risk_config.get("take_profit_percent", 2.0)

            self.info.append(f"Max positions: {max_pos}")
            self.info.append(f"Lot size: {lot_size}")
            self.info.append(f"Stop loss: {sl}%")
            self.info.append(f"Take profit: {tp}%")

        except Exception as e:
            self.issues.append(f"Trading rules check error: {e}")

    def check_signal_generation(self):
        """Test signal generation with current data."""
        self.logger.info("[8/9] Testing Signal Generation...")
        try:
            strategy_manager = StrategyManager(self.db, mode="live")

            # Try to generate signals
            test_symbol = self.db.get_symbol_sample(limit=1)

            if not test_symbol:
                self.warnings.append(
                    "Cannot test signal generation - no pairs available"
                )
                return

            test_symbol = test_symbol[0] if test_symbol else None
            signals = strategy_manager.generate_signals()

            if signals:
                self.info.append(
                    f"[OK] Signal generation works - generated {len(signals)} signals"
                )
                for sig in signals[:3]:
                    self.info.append(
                        f"  {sig.get('symbol')} {sig.get('action').upper()}"
                    )
            else:
                self.warnings.append(
                    "No signals generated - check data or strategy parameters"
                )

        except Exception as e:
            self.issues.append(f"Signal generation error: {e}")

    def check_volatility_ranking(self):
        """Test volatility-based pair ranking."""
        self.logger.info("[9/9] Checking Volatility Ranking...")
        try:
            volatility_config = self.config.get("volatility", {})
            top_n = volatility_config.get("top_n_pairs", 10)

            # Get list of tradable pairs
            tradable_pairs = self.db.get_symbol_sample(limit=20)

            if not tradable_pairs:
                self.warnings.append("No tradable pairs - cannot rank volatility")
                return

            # Get ranked pairs for first timeframe
            ranked_pairs = volatility_rank_pairs(
                self.db,
                tradable_pairs,
                15,
                lookback_bars=volatility_config.get("lookback_bars", 200),
            )

            if ranked_pairs:
                self.info.append(
                    f"Volatility ranking available - top {min(len(ranked_pairs), top_n)} pairs"
                )
                for rank, pair_info in enumerate(ranked_pairs[:5], 1):
                    symbol = pair_info.get("symbol", "unknown")
                    atr = pair_info.get("atr", 0)
                    self.info.append(f"  {rank}. {symbol} (ATR: {atr:.6f})")
            else:
                self.warnings.append("Volatility ranking unavailable - check data")

        except Exception as e:
            self.issues.append(f"Volatility ranking error: {e}")

    def _print_report(self, report: Dict):
        """Print diagnostic report to logs."""
        self.logger.info("\n" + "=" * 70)
        self.logger.info("DIAGNOSTIC REPORT")
        self.logger.info("=" * 70)

        self.logger.info(f"\nStatus: {report['status']}")
        self.logger.info(
            f"Can Trade: {'YES [OK]' if report['can_trade'] else 'NO [BLOCKED]'}"
        )

        if report["issues"]:
            self.logger.error(f"\n[CRITICAL] ISSUES ({len(report['issues'])}):")
            for issue in report["issues"]:
                self.logger.error(f"  - {issue}")

        if report["warnings"]:
            self.logger.warning(f"\n[WARNING] ({len(report['warnings'])}):")
            for warning in report["warnings"]:
                self.logger.warning(f"  - {warning}")

        if report["info"]:
            self.logger.info(f"\n[INFO] ({len(report['info'])}):")
            for info in report["info"]:
                self.logger.info(f"  - {info}")

        self.logger.info("\n" + "=" * 70)

    @staticmethod
    def get_blockers_summary(report: Dict) -> str:
        """Get summary of what's blocking live trading.

        Args:
            report: Diagnostic report from run_full_diagnostic()

        Returns:
            Human-readable summary of blockers
        """
        if not report["issues"]:
            return "[OK] No blockers - live trading should work"

        summary = "Live trading is blocked by:\n"
        for i, issue in enumerate(report["issues"], 1):
            summary += f"{i}. {issue}\n"

        return summary
