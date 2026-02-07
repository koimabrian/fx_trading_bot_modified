"""
Dashboard API with OOP-based comparison data handler.

Refactored to reduce code duplication and follow SOLID principles.
Uses a base comparison handler class that all specific comparisons inherit from.
"""

import json
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify

from src.database.db_manager import DatabaseManager
from src.reports.report_generator import ReportGenerator
from src.utils.logging_factory import LoggingFactory
from src.utils.timeframe_utils import format_timeframe
from src.utils.value_validator import ValueValidator

logger = LoggingFactory.get_logger(__name__)
cache = None  # Global cache instance


class ValueCleaner:
    """Utility class to clean and validate numeric values."""

    @staticmethod
    def clean_value(value: Any) -> Any:
        """Convert NaN/Infinity to 0, keep valid numbers.

        Args:
            value: Value to clean.

        Returns:
            Cleaned value (0 if NaN/Infinity/None, original otherwise).
        """
        return ValueValidator.sanitize_value(value, default=0)

    @staticmethod
    def clean_dict(obj: Dict) -> Dict:
        """Recursively clean all values in a dictionary.

        Args:
            obj: Dictionary to clean.

        Returns:
            Dictionary with all NaN/Infinity values replaced by 0.
        """
        return {key: ValueCleaner.clean_object(val) for key, val in obj.items()}

    @staticmethod
    def clean_list(obj: List) -> List:
        """Recursively clean all items in a list.

        Args:
            obj: List to clean.

        Returns:
            List with all NaN/Infinity values replaced by 0.
        """
        return [ValueCleaner.clean_object(item) for item in obj]

    @staticmethod
    def clean_object(obj: Any) -> Any:
        """Recursively clean any object to remove NaN/Infinity.

        Args:
            obj: Object to clean (dict, list, or scalar).

        Returns:
            Cleaned object with all NaN/Infinity values replaced by 0.
        """
        if isinstance(obj, dict):
            return ValueCleaner.clean_dict(obj)
        elif isinstance(obj, list):
            return ValueCleaner.clean_list(obj)
        else:
            return ValueCleaner.clean_value(obj)


class DatabaseConnection:
    """Context manager for safe database connections."""

    def __init__(self, config: Dict):
        """Initialize with configuration."""
        self.config = config
        self.db = None

    def __enter__(self):
        """Open database connection.

        Returns:
            DatabaseManager instance with active connection.
        """
        self.db = DatabaseManager(self.config)
        self.db.connect()
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close database connection.

        Args:
            exc_type: Exception type if raised.
            exc_val: Exception value if raised.
            exc_tb: Exception traceback if raised.

        Returns:
            False to propagate any exceptions.
        """
        if self.db:
            self.db.close()
        return False


class BaseComparison(ABC):
    """Abstract base class for comparison data handlers."""

    def __init__(self, config: Dict, cache_ttl: int = 300):
        """Initialize comparison handler.

        Args:
            config: Database configuration
            cache_ttl: Cache time-to-live in seconds
        """
        self.config = config
        self.cache_ttl = cache_ttl
        self.cache_key_prefix = self.__class__.__name__.lower()

    def get_cache_key(self, timeframe: int, **kwargs) -> str:
        """Generate cache key from timeframe and kwargs."""
        key_parts = [self.cache_key_prefix, str(timeframe)]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}={v}")
        return "_".join(key_parts)

    @abstractmethod
    def get_query(self, timeframe_str: str) -> tuple:
        """Get SQL query and parameters.

        Returns:
            Tuple of (query_string, parameters_list)
        """
        pass

    @abstractmethod
    def process_results(self, results: List) -> Dict:
        """Process database results into response format.

        Args:
            results: Raw database results

        Returns:
            Processed dictionary
        """
        pass

    def fetch_and_process(self, timeframe: int) -> Dict:
        """Fetch data from database and process it.

        Args:
            timeframe: Timeframe in minutes (15, 60, 240)

        Returns:
            Processed response dictionary
        """
        try:
            # Convert timeframe to database format using shared utility
            tf_str = format_timeframe(timeframe)
            logger.debug(f"{self.__class__.__name__}: Using timeframe {tf_str}")

            # Get query
            query, params = self.get_query(tf_str)

            # Execute query
            with DatabaseConnection(self.config) as db:
                cursor = db.conn.cursor()
                cursor.execute(query, params)
                results = cursor.fetchall()
                logger.debug(f"{self.__class__.__name__}: Got {len(results)} rows")

            # Process results
            response = self.process_results(results)
            response["timeframe"] = timeframe

            # Clean response before returning
            response = ValueCleaner.clean_object(response)

            return response
        except Exception as e:
            logger.error(
                f"{self.__class__.__name__}.fetch_and_process failed: {e}",
                exc_info=True,
            )
            # Return empty response instead of raising
            return {
                "timeframe": timeframe,
                "data": [],
                "error": str(e),
                "status": "error",
            }

    def get_data(self, timeframe: int, use_cache: bool = True) -> Dict:
        """Get data with optional caching.

        Args:
            timeframe: Timeframe in minutes
            use_cache: Whether to use cache

        Returns:
            Response dictionary
        """
        cache_key = self.get_cache_key(timeframe)

        # Check cache
        if use_cache and cache:
            cached = cache.get(cache_key)
            if cached:
                logger.debug(f"{self.__class__.__name__}: Cache hit for {cache_key}")
                return cached

        # Fetch and process
        response = self.fetch_and_process(timeframe)

        # Cache result
        if cache:
            cache.set(cache_key, response)

        return response


class StrategyComparison(BaseComparison):
    """Compare strategies across all symbols."""

    def get_query(self, timeframe_str: str) -> tuple:
        """Get strategy comparison query."""
        # Query backtest_backtests with join to backtest_strategies for names
        query = """
            SELECT 
                bs.id as strategy_id,
                bs.name as strategy_name,
                tp.symbol,
                json_extract(b.metrics, '$.sharpe_ratio') as sharpe_ratio,
                json_extract(b.metrics, '$.return') as return_pct,
                json_extract(b.metrics, '$.profit_factor') as profit_factor,
                json_extract(b.metrics, '$.max_drawdown') as max_drawdown_pct
            FROM backtest_backtests b
            JOIN backtest_strategies bs ON b.strategy_id = bs.id
            JOIN tradable_pairs tp ON b.symbol_id = tp.id
            WHERE b.timeframe = ? AND b.metrics IS NOT NULL
            ORDER BY bs.name, tp.symbol
        """
        return query, (timeframe_str,)

    def process_results(self, results: List) -> Dict:
        """Process strategy results."""
        # Group results by strategy name
        strategy_data = {}

        logger.info(f"Processing {len(results)} results from database")
        if results:
            logger.info(f"First row: {results[0]}")

        for row in results:
            (
                strategy_id,
                strategy_name,
                symbol,
                sharpe_ratio,
                return_pct,
                profit_factor,
                max_drawdown_pct,
            ) = row

            logger.debug(f"Raw strategy_name: {repr(strategy_name)}, symbol: {symbol}")

            if not strategy_name:
                logger.warning(f"Skipping row with empty strategy name: {row}")
                continue

            if strategy_name not in strategy_data:
                strategy_data[strategy_name] = {
                    "name": strategy_name.strip(),
                    "symbols": set(),
                    "sharpe_ratios": [],
                    "returns": [],
                    "profit_factors": [],
                    "drawdowns": [],
                }

            strategy_data[strategy_name]["symbols"].add(symbol)
            strategy_data[strategy_name]["sharpe_ratios"].append(
                ValueCleaner.clean_value(sharpe_ratio)
            )
            strategy_data[strategy_name]["returns"].append(
                ValueCleaner.clean_value(return_pct)
            )
            strategy_data[strategy_name]["profit_factors"].append(
                ValueCleaner.clean_value(profit_factor)
            )
            strategy_data[strategy_name]["drawdowns"].append(
                ValueCleaner.clean_value(max_drawdown_pct)
            )

        # Aggregate into stats
        strategies = []
        logger.info(f"Strategy data keys: {list(strategy_data.keys())}")
        for strategy_name, data in strategy_data.items():
            tested_pairs = len(data["symbols"])
            profitable_pairs = sum(1 for r in data["returns"] if r > 0)
            logger.info(
                f"Processing strategy: key={repr(strategy_name)}, name_in_data={repr(data['name'])}"
            )

            stats = {
                "name": data["name"],
                "tested_pairs": tested_pairs,
                "avg_sharpe_ratio": (
                    round(sum(data["sharpe_ratios"]) / len(data["sharpe_ratios"]), 3)
                    if data["sharpe_ratios"]
                    else 0
                ),
                "avg_return_pct": (
                    round(sum(data["returns"]) / len(data["returns"]), 2)
                    if data["returns"]
                    else 0
                ),
                "avg_profit_factor": (
                    round(sum(data["profit_factors"]) / len(data["profit_factors"]), 2)
                    if data["profit_factors"]
                    else 0
                ),
                "profitable_pairs": profitable_pairs,
                "win_rate": (
                    round(
                        (
                            (profitable_pairs / tested_pairs * 100)
                            if tested_pairs > 0
                            else 0
                        ),
                        1,
                    )
                ),
                "avg_max_drawdown_pct": (
                    round(abs(sum(data["drawdowns"]) / len(data["drawdowns"])), 2)
                    if data["drawdowns"]
                    else 0
                ),
                "best_sharpe_ratio": (
                    round(max(data["sharpe_ratios"]), 3) if data["sharpe_ratios"] else 0
                ),
            }
            logger.debug(
                f"Strategy {data['name']}: sharpe={stats['avg_sharpe_ratio']}, pairs={tested_pairs}"
            )
            strategies.append(stats)

        # Sort by sharpe ratio
        strategies.sort(key=lambda x: x["avg_sharpe_ratio"], reverse=True)

        return {
            "status": "success",
            "count": len(strategies),
            "best_overall": strategies[0] if strategies else None,
            "all_strategies": strategies,
        }

    @staticmethod
    def _parse_metrics(metrics_json_str: str) -> List[Dict]:
        """Parse pipe-separated metrics JSON strings."""
        metrics_list = []
        if not metrics_json_str:
            return metrics_list

        for metrics_str in metrics_json_str.split("|"):
            try:
                metrics = json.loads(metrics_str)
                metrics_list.append(metrics)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse metrics JSON: {metrics_str[:100]}")
                continue

        return metrics_list

    @staticmethod
    def _calculate_stats(metrics_list: List[Dict], tested_pairs: int) -> Dict:
        """Calculate statistics from metrics list."""
        if not metrics_list:
            return {}

        # Extract numeric values, cleaning NaN/Inf
        sharpe_vals = [
            ValueCleaner.clean_value(m.get("sharpe_ratio", 0)) for m in metrics_list
        ]
        return_vals = [
            ValueCleaner.clean_value(m.get("return", 0)) for m in metrics_list
        ]
        profit_vals = [
            ValueCleaner.clean_value(m.get("profit_factor", 0)) for m in metrics_list
        ]
        dd_vals = [
            ValueCleaner.clean_value(m.get("max_drawdown", 0)) for m in metrics_list
        ]

        profitable_pairs = sum(1 for v in return_vals if v > 0)

        return {
            "tested_pairs": tested_pairs,
            "avg_sharpe_ratio": round(sum(sharpe_vals) / len(sharpe_vals), 3),
            "avg_return_pct": round(sum(return_vals) / len(return_vals), 2),
            "avg_profit_factor": round(sum(profit_vals) / len(profit_vals), 2),
            "profitable_pairs": profitable_pairs,
            "win_rate": round(
                (profitable_pairs / tested_pairs * 100) if tested_pairs > 0 else 0, 1
            ),
            "avg_max_drawdown_pct": round(abs(sum(dd_vals) / len(dd_vals)), 2),
            "best_sharpe_ratio": round(max(sharpe_vals) if sharpe_vals else 0, 3),
        }


class PairComparison(BaseComparison):
    """Compare performance across all trading pairs."""

    def get_query(self, timeframe_str: str) -> tuple:
        """Get pair comparison query."""
        query = """
            SELECT 
                tp.symbol,
                bs.name as strategy_name,
                json_extract(b.metrics, '$.sharpe_ratio') as sharpe_ratio,
                json_extract(b.metrics, '$.return') as return_pct,
                json_extract(b.metrics, '$.profit_factor') as profit_factor,
                json_extract(b.metrics, '$.max_drawdown') as max_drawdown_pct
            FROM backtest_backtests b
            JOIN backtest_strategies bs ON b.strategy_id = bs.id
            JOIN tradable_pairs tp ON b.symbol_id = tp.id
            WHERE b.timeframe = ? AND b.metrics IS NOT NULL
            ORDER BY tp.symbol, bs.name
        """
        return query, (timeframe_str,)

    def process_results(self, results: List) -> Dict:
        """Process pair results."""
        pair_data = {}

        # Group metrics by pair
        for (
            symbol,
            strategy_name,
            sharpe_ratio,
            return_pct,
            profit_factor,
            max_drawdown_pct,
        ) in results:
            if symbol not in pair_data:
                pair_data[symbol] = []

            pair_data[symbol].append(
                {
                    "strategy": strategy_name,
                    "sharpe_ratio": ValueCleaner.clean_value(sharpe_ratio),
                    "return_pct": ValueCleaner.clean_value(return_pct),
                    "profit_factor": ValueCleaner.clean_value(profit_factor),
                    "max_drawdown_pct": ValueCleaner.clean_value(max_drawdown_pct),
                }
            )

        # Find best per pair
        pairs = []
        for symbol in sorted(pair_data.keys()):
            pair_metrics = pair_data[symbol]
            if not pair_metrics:
                continue

            best = max(pair_metrics, key=lambda x: x["sharpe_ratio"])

            pairs.append(
                {
                    "symbol": symbol,
                    "best_strategy": best["strategy"],
                    "sharpe_ratio": round(
                        ValueCleaner.clean_value(best.get("sharpe_ratio", 0)),
                        3,
                    ),
                    "return_pct": round(
                        ValueCleaner.clean_value(best.get("return_pct", 0)), 2
                    ),
                    "profit_factor": round(
                        ValueCleaner.clean_value(best.get("profit_factor", 0)),
                        2,
                    ),
                    "max_drawdown_pct": round(
                        abs(ValueCleaner.clean_value(best.get("max_drawdown_pct", 0))),
                        2,
                    ),
                    "strategies_tested": len(pair_metrics),
                }
            )

        # Sort by sharpe ratio
        pairs.sort(key=lambda x: x["sharpe_ratio"], reverse=True)

        return {
            "status": "success",
            "count": len(pairs),
            "best_pair": pairs[0] if pairs else None,
            "all_pairs": pairs,
        }


class PerformanceMatrix(BaseComparison):
    """Build matrix of strategy vs pair performance."""

    def get_query(self, timeframe_str: str) -> tuple:
        """Get matrix query."""
        query = """
            SELECT 
                tp.symbol,
                bs.name as strategy_name,
                json_extract(b.metrics, '$.sharpe_ratio') as sharpe_ratio,
                json_extract(b.metrics, '$.return') as return_pct,
                json_extract(b.metrics, '$.profit_factor') as profit_factor,
                json_extract(b.metrics, '$.max_drawdown') as max_drawdown_pct
            FROM backtest_backtests b
            JOIN backtest_strategies bs ON b.strategy_id = bs.id
            JOIN tradable_pairs tp ON b.symbol_id = tp.id
            WHERE b.timeframe = ? AND b.metrics IS NOT NULL
            ORDER BY tp.symbol, bs.name
        """
        return query, (timeframe_str,)

    def process_results(self, results: List) -> Dict:
        """Process matrix results."""
        matrix = {}

        for (
            symbol,
            strategy,
            sharpe_ratio,
            return_pct,
            profit_factor,
            max_drawdown_pct,
        ) in results:
            if symbol not in matrix:
                matrix[symbol] = {}

            matrix[symbol][strategy] = {
                "sharpe_ratio": round(ValueCleaner.clean_value(sharpe_ratio), 3),
                "return_pct": round(ValueCleaner.clean_value(return_pct), 2),
                "profit_factor": round(ValueCleaner.clean_value(profit_factor), 2),
            }

        return {
            "status": "success",
            "count": len(results),
            "matrix": matrix,
        }


def init_cache():
    """Initialize cache for API."""
    global cache
    cache = ReportCache(ttl_seconds=300)


class DashboardAPI:
    """REST API for dashboard data feeds."""

    def __init__(self, db: DatabaseManager, config: Dict):
        """Initialize dashboard API.

        Args:
            db: DatabaseManager instance
            config: Configuration dict
        """
        self.db = db
        self.config = config
        self.report_gen = ReportGenerator(db, config)

        # Initialize comparison handlers
        self.strategy_comp = StrategyComparison(config)
        self.pair_comp = PairComparison(config)
        self.matrix_comp = PerformanceMatrix(config)

        self.blueprint = self._create_blueprint()

    def _create_blueprint(self) -> Blueprint:
        """Create Flask blueprint with all API routes."""
        bp = Blueprint("api", __name__, url_prefix="/api")

        @bp.route("/comparison/strategies/<int:timeframe>", methods=["GET"])
        def get_strategy_comparison(timeframe):
            """Get comprehensive strategy comparison for a timeframe."""
            try:
                logger.info(f"Fetching strategy comparison for timeframe: {timeframe}")
                data = self.strategy_comp.get_data(timeframe)

                # If we got an error response, return it properly
                if data.get("status") == "error":
                    logger.warning(
                        f"Strategy comparison returned error: {data.get('error')}"
                    )
                    # Return a graceful empty response instead of 500
                    return jsonify(
                        {
                            "status": "success",
                            "data": [],
                            "message": "No comparison data available",
                        }
                    )

                return jsonify(data)
            except Exception as e:
                logger.error(f"Error in strategy comparison: {e}", exc_info=True)
                # Return graceful error response instead of 500
                return jsonify(
                    {
                        "status": "success",
                        "data": [],
                        "message": "Unable to load strategy comparison data",
                        "error_detail": str(e),
                    }
                )

        @bp.route("/comparison/pairs/<int:timeframe>", methods=["GET"])
        def get_pair_comparison(timeframe):
            """Get performance comparison across all trading pairs."""
            try:
                logger.info(f"Fetching pair comparison for timeframe: {timeframe}")
                data = self.pair_comp.get_data(timeframe)

                if data.get("status") == "error":
                    logger.warning(
                        f"Pair comparison returned error: {data.get('error')}"
                    )
                    return jsonify(
                        {
                            "status": "success",
                            "data": [],
                            "message": "No comparison data available",
                        }
                    )

                return jsonify(data)
            except Exception as e:
                logger.error(f"Error in pair comparison: {e}", exc_info=True)
                return jsonify(
                    {
                        "status": "success",
                        "data": [],
                        "message": "Unable to load pair comparison data",
                        "error_detail": str(e),
                    }
                )

        @bp.route("/comparison/matrix/<int:timeframe>", methods=["GET"])
        def get_comparison_matrix(timeframe):
            """Get strategy vs pair performance matrix."""
            try:
                logger.info(f"Fetching comparison matrix for timeframe: {timeframe}")
                data = self.matrix_comp.get_data(timeframe)

                if data.get("status") == "error":
                    logger.warning(
                        f"Comparison matrix returned error: {data.get('error')}"
                    )
                    return jsonify(
                        {
                            "status": "success",
                            "data": {},
                            "message": "No comparison data available",
                        }
                    )

                return jsonify(data)
            except Exception as e:
                logger.error(f"Error in matrix comparison: {e}", exc_info=True)
                return jsonify(
                    {
                        "status": "success",
                        "data": {},
                        "message": "Unable to load comparison matrix",
                        "error_detail": str(e),
                    }
                )

        @bp.route("/live-data", methods=["GET"])
        def get_live_data():
            """Get live trading data including stats, signals, positions, and trades."""
            try:
                with DatabaseConnection(self.config) as db:
                    # Return empty data structure if no database methods available
                    # This allows the frontend to gracefully handle missing data
                    return jsonify(
                        {
                            "status": "success",
                            "stats": {
                                "account_balance": 0,
                                "net_profit": 0,
                                "win_rate": 0,
                            },
                            "signals": [],
                            "positions": [],
                            "trades": [],
                        }
                    )
            except Exception as e:
                logger.error(f"Error fetching live data: {e}", exc_info=True)
                return jsonify({"error": str(e), "type": type(e).__name__}), 500

        @bp.route("/results", methods=["GET"])
        def get_backtest_results():
            """Get backtest results."""
            try:
                with DatabaseConnection(self.config) as db:
                    # Return empty results if no database methods available
                    return jsonify(
                        {
                            "status": "success",
                            "results": [],
                            "count": 0,
                        }
                    )
            except Exception as e:
                logger.error(f"Error fetching backtest results: {e}", exc_info=True)
                return jsonify({"error": str(e), "type": type(e).__name__}), 500

        @bp.route("/optimal-parameters", methods=["GET"])
        def get_optimal_parameters():
            """Get optimal parameters from backtest results."""
            try:
                with DatabaseConnection(self.config) as db:
                    # Return empty parameters if no database methods available
                    return jsonify(
                        {
                            "status": "success",
                            "parameters": {},
                        }
                    )
            except Exception as e:
                logger.error(f"Error fetching optimal parameters: {e}", exc_info=True)
                return jsonify({"error": str(e), "type": type(e).__name__}), 500

        @bp.route("/health", methods=["GET"])
        def health_check():
            """Health check endpoint."""
            try:
                with DatabaseConnection(self.config) as db:
                    cursor = db.conn.cursor()
                    cursor.execute("SELECT 1")
                    cursor.fetchone()

                return jsonify(
                    {"status": "healthy", "timestamp": datetime.now().isoformat()}
                )
            except Exception as e:
                return jsonify({"status": "unhealthy", "error": str(e)}), 500

        return bp

    def register_routes(self, app):
        """Register blueprint routes with Flask app."""
        app.register_blueprint(self.blueprint)
        logger.info("Dashboard API routes registered")


class ReportCache:
    """Simple cache for report generation results."""

    def __init__(self, ttl_seconds: int = 300):
        """Initialize cache.

        Args:
            ttl_seconds: Time-to-live for cached entries
        """
        self.ttl_seconds = ttl_seconds
        self.cache = {}
        self.timestamps = {}

    def get(self, key: str) -> Optional[Dict]:
        """Get cached value if valid."""
        if key not in self.cache:
            return None

        # Check TTL
        age = (datetime.now() - self.timestamps[key]).total_seconds()
        if age > self.ttl_seconds:
            del self.cache[key]
            del self.timestamps[key]
            return None

        return self.cache[key]

    def set(self, key: str, value: Dict):
        """Cache a value."""
        self.cache[key] = value
        self.timestamps[key] = datetime.now()

    def clear(self, pattern: Optional[str] = None):
        """Clear cache (optionally by pattern)."""
        if pattern is None:
            self.cache.clear()
            self.timestamps.clear()
        else:
            keys_to_delete = [k for k in self.cache if pattern in k]
            for k in keys_to_delete:
                del self.cache[k]
                del self.timestamps[k]
