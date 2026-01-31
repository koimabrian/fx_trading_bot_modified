"""Parameter archiving and optimal strategy selection for the FX Trading Bot.

Manages storage and retrieval of optimal strategy parameters from backtesting
results. Implements the parameter fallback strategy for live trading.
"""

import json
import logging
import sqlite3
from typing import Any, Dict, List, Optional

from src.utils.logging_factory import LoggingFactory


class ParameterArchiver:
    """Manages archiving and retrieval of optimal strategy parameters."""

    def __init__(self, db, config: Dict):
        """Initialize ParameterArchiver.

        Args:
            db: Database manager instance
            config: Configuration dictionary
        """
        self.db = db
        self.config = config
        self.logger = LoggingFactory.get_logger(__name__)

    def store_optimal_parameters(
        self,
        symbol: str,
        timeframe: str,
        strategy_name: str,
        params: Dict[str, Any],
        metrics: Dict[str, float],
    ) -> bool:
        """Store optimal strategy parameters for a symbol/timeframe combination.

        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            timeframe: Timeframe string (e.g., 'M15', 'H1')
            strategy_name: Strategy name (e.g., 'rsi', 'macd')
            params: Parameter dictionary
            metrics: Backtest metrics including sharpe_ratio, return_pct, etc.

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.db.conn.cursor()

            # Insert or replace optimal parameters
            cursor.execute(
                """
                INSERT OR REPLACE INTO optimal_parameters
                (symbol, timeframe, strategy_name, parameter_value, metrics, last_optimized)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (
                    symbol,
                    timeframe,
                    strategy_name,
                    json.dumps(params),
                    json.dumps(metrics),
                ),
            )

            self.db.conn.commit()
            self.logger.info(
                "Stored optimal params: %s (%s %s) - Sharpe: %.2f",
                strategy_name,
                symbol,
                timeframe,
                metrics.get("sharpe_ratio", 0),
            )
            return True

        except sqlite3.Error as e:
            self.logger.error(
                "Failed to store optimal parameters for %s (%s %s): %s",
                strategy_name,
                symbol,
                timeframe,
                e,
            )
            return False

    def load_optimal_parameters(
        self, symbol: str, timeframe: str, strategy_name: str
    ) -> Optional[Dict[str, Any]]:
        """Load optimal parameters for a specific symbol/timeframe/strategy.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe string
            strategy_name: Strategy name

        Returns:
            Parameter dictionary if found, None otherwise
        """
        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                """
                SELECT parameter_value, metrics, last_optimized FROM optimal_parameters op
                JOIN tradable_pairs tp ON op.symbol_id = tp.id
                WHERE tp.symbol = ? AND op.timeframe = ? AND op.strategy_name = ?
                ORDER BY op.last_optimized DESC LIMIT 1
            """,
                (symbol, timeframe, strategy_name),
            )

            row = cursor.fetchone()
            if not row:
                return None

            params = json.loads(row[0])
            metrics = json.loads(row[1])
            params["_metrics"] = metrics  # Attach metrics for reference
            params["_last_optimized"] = row[2]

            self.logger.debug(
                "Loaded optimal params: %s (%s %s) - Sharpe: %.2f",
                strategy_name,
                symbol,
                timeframe,
                metrics.get("sharpe_ratio", 0),
            )

            return params

        except sqlite3.Error as e:
            self.logger.error(
                "Failed to load optimal parameters for %s (%s %s): %s",
                strategy_name,
                symbol,
                timeframe,
                e,
            )
            return None

    def load_all_optimal_parameters(self) -> Dict[str, Dict[str, Any]]:
        """Load all optimal parameters from database.

        Returns:
            Dictionary keyed by 'symbol_timeframe_strategy'
        """
        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                """
                SELECT symbol, timeframe, strategy_name, parameter_value, metrics
                FROM optimal_parameters
                ORDER BY last_optimized DESC
            """
            )

            all_params = {}
            for row in cursor.fetchall():
                symbol, timeframe, strategy_name, params_json, metrics_json = row
                key = f"{symbol}_{timeframe}_{strategy_name}"
                params = json.loads(params_json)
                params["_metrics"] = json.loads(metrics_json)
                all_params[key] = params

            self.logger.info("Loaded %d optimal parameter sets", len(all_params))
            return all_params

        except sqlite3.Error as e:
            self.logger.error("Failed to load all optimal parameters: %s", e)
            return {}

    def query_top_strategies_by_rank(
        self, symbol: str, timeframe: str, limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Query top performing strategies for a symbol/timeframe by rank score.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe string
            limit: Number of top strategies to return

        Returns:
            List of strategy dictionaries with parameters and metrics
        """
        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                """
                SELECT br.strategy_name, br.metrics, op.parameter_value
                FROM backtest_results br
                JOIN tradable_pairs tp ON br.symbol = tp.symbol
                LEFT JOIN optimal_parameters op
                    ON op.symbol_id = tp.id
                    AND op.timeframe = br.timeframe
                    AND op.strategy_name = br.strategy_name
                WHERE tp.symbol = ? AND br.timeframe = ?
                ORDER BY br.rank_score DESC
                LIMIT ?
            """,
                (symbol, timeframe, limit),
            )

            strategies = []
            for row in cursor.fetchall():
                strategy_name, metrics_json, params_json = row
                strategy_dict = {
                    "strategy_name": strategy_name,
                    "metrics": json.loads(metrics_json) if metrics_json else {},
                    "parameters": json.loads(params_json) if params_json else {},
                }
                strategies.append(strategy_dict)

            if strategies:
                self.logger.debug(
                    "Top %d strategies for %s (%s): %s",
                    len(strategies),
                    symbol,
                    timeframe,
                    [s["strategy_name"] for s in strategies],
                )

            return strategies

        except sqlite3.Error as e:
            self.logger.error(
                "Failed to query top strategies for %s (%s): %s", symbol, timeframe, e
            )
            return []

    def has_parameters(self, symbol: str, timeframe: str) -> bool:
        """Check if optimal parameters exist for a symbol/timeframe.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe string

        Returns:
            True if parameters exist, False otherwise
        """
        try:
            cursor = self.db.conn.cursor()
            cursor.execute(
                """
                SELECT COUNT(*) FROM optimal_parameters op
                JOIN tradable_pairs tp ON op.symbol_id = tp.id
                WHERE tp.symbol = ? AND op.timeframe = ?
            """,
                (symbol, timeframe),
            )
            count = cursor.fetchone()[0]
            return count > 0

        except sqlite3.Error as e:
            self.logger.error(
                "Failed to check parameters for %s (%s): %s", symbol, timeframe, e
            )
            return False
