"""
Dashboard API endpoints for report data feeds.

Exposes REST endpoints to feed real-time and historical metrics to the dashboard.
Includes caching for performance.
"""

import logging
from typing import Dict, List, Optional, Tuple
from functools import lru_cache
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request

from src.reports.report_generator import ReportGenerator
from src.database.db_manager import DatabaseManager


logger = logging.getLogger(__name__)
cache = None  # Global cache instance


def init_cache():
    """Initialize cache for API."""
    global cache
    cache = ReportCache(ttl_seconds=300)


class DashboardAPI:
    """REST API for dashboard data feeds."""

    def __init__(self, db: DatabaseManager, config: Dict):
        """
        Initialize dashboard API.

        Args:
            db: DatabaseManager instance
            config: Configuration dict
        """
        self.db = db
        self.config = config
        self.report_gen = ReportGenerator(db, config)
        self.blueprint = self._create_blueprint()

    def _create_blueprint(self) -> Blueprint:
        """Create Flask blueprint with all API routes."""
        bp = Blueprint("api", __name__, url_prefix="/api")

        @bp.route(
            "/reports/strategy/<strategy>/<symbol>/<int:timeframe>", methods=["GET"]
        )
        def get_strategy_report(strategy, symbol, timeframe):
            """Get performance report for specific strategy/symbol/timeframe."""
            try:
                df = self.report_gen.generate_strategy_performance(
                    symbol=symbol,
                    strategy=strategy,
                    timeframe=timeframe,
                )

                if df is None:
                    return jsonify({"error": "No data found"}), 404

                return jsonify(
                    {
                        "status": "success",
                        "data": df.to_dict("records")[0] if len(df) > 0 else {},
                    }
                )

            except Exception as e:
                logger.error(f"Error in get_strategy_report: {e}")
                return jsonify({"error": str(e)}), 500

        @bp.route("/reports/comparison/<int:timeframe>", methods=["GET"])
        def get_comparison_report(timeframe):
            """Get multi-symbol strategy comparison."""
            strategy = request.args.get("strategy", "rsi")

            try:
                df = self.report_gen.generate_multi_symbol_comparison(
                    strategy=strategy,
                    timeframe=timeframe,
                )

                if df is None:
                    return jsonify({"error": "No data found"}), 404

                return jsonify(
                    {
                        "status": "success",
                        "count": len(df),
                        "data": df.to_dict("records"),
                    }
                )

            except Exception as e:
                logger.error(f"Error in get_comparison_report: {e}")
                return jsonify({"error": str(e)}), 500

        @bp.route("/reports/volatility/<int:timeframe>", methods=["GET"])
        def get_volatility_report(timeframe):
            """Get volatility ranking for timeframe."""
            try:
                df = self.report_gen.generate_volatility_ranking(timeframe)

                if df is None:
                    return jsonify({"error": "No data found"}), 404

                return jsonify(
                    {
                        "status": "success",
                        "count": len(df),
                        "data": df.to_dict("records"),
                    }
                )

            except Exception as e:
                logger.error(f"Error in get_volatility_report: {e}")
                return jsonify({"error": str(e)}), 500

        @bp.route("/metrics/summary", methods=["GET"])
        def get_summary_metrics():
            """Get overall summary metrics."""
            try:
                summary = self.report_gen.get_summary_metrics()

                if summary is None:
                    return jsonify({"error": "No data found"}), 404

                return jsonify({"status": "success", "data": summary})

            except Exception as e:
                logger.error(f"Error in get_summary_metrics: {e}")
                return jsonify({"error": str(e)}), 500

        @bp.route("/trades/recent", methods=["GET"])
        def get_recent_trades():
            """Get recent live trades."""
            limit = request.args.get("limit", 50, type=int)

            try:
                cursor = self.db.conn.cursor()
                query = """
                    SELECT 
                        id,
                        symbol,
                        strategy_name,
                        entry_price,
                        exit_price,
                        pnl,
                        status,
                        created_at
                    FROM trades
                    ORDER BY created_at DESC
                    LIMIT ?
                """

                cursor.execute(query, (limit,))
                results = cursor.fetchall()

                trades = []
                for row in results:
                    trades.append(
                        {
                            "id": row[0],
                            "symbol": row[1],
                            "strategy": row[2],
                            "entry_price": row[3],
                            "exit_price": row[4],
                            "pnl": row[5],
                            "status": row[6],
                            "created_at": row[7],
                        }
                    )

                return jsonify(
                    {"status": "success", "count": len(trades), "data": trades}
                )

            except Exception as e:
                logger.error(f"Error in get_recent_trades: {e}")
                return jsonify({"error": str(e)}), 500

        @bp.route("/comparison/strategies/<int:timeframe>", methods=["GET"])
        def get_strategy_comparison(timeframe):
            """Get comprehensive strategy comparison for a timeframe.

            Compares all strategies across all symbols with:
            - Best overall strategy (highest Sharpe ratio)
            - Profitable strategies (positive return)
            - Average metrics per strategy
            """
            cache_key = f"strategy_comparison_{timeframe}"
            if cache and cache.get(cache_key):
                return jsonify(cache.get(cache_key))

            try:
                cursor = self.db.conn.cursor()

                # Query strategy performance metrics
                query = """
                    SELECT 
                        bs.name as strategy,
                        COUNT(*) as tested_pairs,
                        AVG(CAST(json_extract(b.metrics, '$.sharpe_ratio') AS REAL)) as avg_sharpe,
                        AVG(CAST(json_extract(b.metrics, '$.return') AS REAL)) as avg_return,
                        AVG(CAST(json_extract(b.metrics, '$.profit_factor') AS REAL)) as avg_profit_factor,
                        SUM(CASE WHEN CAST(json_extract(b.metrics, '$.return') AS REAL) > 0 
                            THEN 1 ELSE 0 END) as profitable_pairs,
                        AVG(CAST(json_extract(b.metrics, '$.max_drawdown') AS REAL)) as avg_max_dd,
                        MAX(CAST(json_extract(b.metrics, '$.sharpe_ratio') AS REAL)) as best_sharpe
                    FROM backtest_backtests b
                    JOIN backtest_strategies bs ON b.strategy_id = bs.id
                    WHERE b.timeframe = ?
                    GROUP BY bs.name
                    ORDER BY avg_sharpe DESC
                """

                cursor.execute(
                    query, (f"M{timeframe}" if timeframe < 60 else f"H{timeframe//60}",)
                )
                results = cursor.fetchall()

                strategies = []
                for row in results:
                    strategies.append(
                        {
                            "name": row[0],
                            "tested_pairs": row[1],
                            "avg_sharpe_ratio": round(row[2] if row[2] else 0, 3),
                            "avg_return_pct": round(row[3] if row[3] else 0, 2),
                            "avg_profit_factor": round(row[4] if row[4] else 0, 2),
                            "profitable_pairs": row[5],
                            "win_rate": round(
                                (row[5] / row[1] * 100) if row[1] > 0 else 0, 1
                            ),
                            "avg_max_drawdown_pct": round(
                                abs(row[6]) if row[6] else 0, 2
                            ),
                            "best_sharpe_ratio": round(row[7] if row[7] else 0, 3),
                        }
                    )

                response = {
                    "status": "success",
                    "timeframe": timeframe,
                    "count": len(strategies),
                    "best_overall": strategies[0] if strategies else None,
                    "all_strategies": strategies,
                }

                if cache:
                    cache.set(cache_key, response)

                return jsonify(response)

            except Exception as e:
                logger.error(f"Error in get_strategy_comparison: {e}")
                return jsonify({"error": str(e)}), 500

        @bp.route("/comparison/pairs/<int:timeframe>", methods=["GET"])
        def get_pair_comparison(timeframe):
            """Get performance comparison across all trading pairs.

            Returns pairs ranked by Sharpe ratio with best strategy per pair.
            """
            strategy = request.args.get("strategy", None)  # Optional filter
            cache_key = f"pair_comparison_{timeframe}_{strategy}"
            if cache and cache.get(cache_key):
                return jsonify(cache.get(cache_key))

            try:
                cursor = self.db.conn.cursor()

                # Query pair performance
                tf_str = f"M{timeframe}" if timeframe < 60 else f"H{timeframe//60}"

                query = """
                    SELECT 
                        tp.symbol,
                        bs.name as best_strategy,
                        CAST(json_extract(b.metrics, '$.sharpe_ratio') AS REAL) as sharpe_ratio,
                        CAST(json_extract(b.metrics, '$.return') AS REAL) as return_pct,
                        CAST(json_extract(b.metrics, '$.profit_factor') AS REAL) as profit_factor,
                        CAST(json_extract(b.metrics, '$.max_drawdown') AS REAL) as max_drawdown,
                        COUNT(*) OVER (PARTITION BY tp.id) as strategies_tested
                    FROM backtest_backtests b
                    JOIN backtest_strategies bs ON b.strategy_id = bs.id
                    JOIN tradable_pairs tp ON b.symbol_id = tp.id
                    WHERE b.timeframe = ?
                      AND b.id IN (
                        SELECT id FROM backtest_backtests 
                        WHERE timeframe = ? AND symbol_id IN (
                            SELECT DISTINCT symbol_id FROM backtest_backtests WHERE timeframe = ?
                        )
                        ORDER BY symbol_id, CAST(json_extract(metrics, '$.sharpe_ratio') AS REAL) DESC
                      )
                    ORDER BY sharpe_ratio DESC, return_pct DESC
                """

                cursor.execute(query, (tf_str, tf_str, tf_str))
                results = cursor.fetchall()

                pairs = []
                seen_pairs = set()
                for row in results:
                    if row[0] not in seen_pairs:  # Keep only best per pair
                        pairs.append(
                            {
                                "symbol": row[0],
                                "best_strategy": row[1],
                                "sharpe_ratio": round(row[2] if row[2] else 0, 3),
                                "return_pct": round(row[3] if row[3] else 0, 2),
                                "profit_factor": round(row[4] if row[4] else 0, 2),
                                "max_drawdown_pct": round(
                                    abs(row[5]) if row[5] else 0, 2
                                ),
                                "strategies_tested": row[6],
                            }
                        )
                        seen_pairs.add(row[0])

                response = {
                    "status": "success",
                    "timeframe": timeframe,
                    "count": len(pairs),
                    "best_pair": pairs[0] if pairs else None,
                    "all_pairs": pairs,
                }

                if cache:
                    cache.set(cache_key, response)

                return jsonify(response)

            except Exception as e:
                logger.error(f"Error in get_pair_comparison: {e}")
                return jsonify({"error": str(e)}), 500

        @bp.route("/comparison/matrix/<int:timeframe>", methods=["GET"])
        def get_comparison_matrix(timeframe):
            """Get strategy vs pair performance matrix.

            Returns a matrix showing each strategy's performance on each pair.
            Useful for identifying optimal strategy-pair combinations.
            """
            cache_key = f"matrix_{timeframe}"
            if cache and cache.get(cache_key):
                return jsonify(cache.get(cache_key))

            try:
                cursor = self.db.conn.cursor()

                tf_str = f"M{timeframe}" if timeframe < 60 else f"H{timeframe//60}"

                # Get all strategy/pair combinations
                query = """
                    SELECT 
                        tp.symbol,
                        bs.name as strategy,
                        CAST(json_extract(b.metrics, '$.sharpe_ratio') AS REAL) as sharpe_ratio,
                        CAST(json_extract(b.metrics, '$.return') AS REAL) as return_pct,
                        CAST(json_extract(b.metrics, '$.profit_factor') AS REAL) as profit_factor
                    FROM backtest_backtests b
                    JOIN backtest_strategies bs ON b.strategy_id = bs.id
                    JOIN tradable_pairs tp ON b.symbol_id = tp.id
                    WHERE b.timeframe = ?
                    ORDER BY tp.symbol, bs.name
                """

                cursor.execute(query, (tf_str,))
                results = cursor.fetchall()

                # Build matrix structure
                matrix = {}
                for row in results:
                    symbol = row[0]
                    strategy = row[1]
                    if symbol not in matrix:
                        matrix[symbol] = {}

                    matrix[symbol][strategy] = {
                        "sharpe_ratio": round(row[2] if row[2] else 0, 3),
                        "return_pct": round(row[3] if row[3] else 0, 2),
                        "profit_factor": round(row[4] if row[4] else 0, 2),
                    }

                response = {
                    "status": "success",
                    "timeframe": timeframe,
                    "matrix": matrix,
                }

                if cache:
                    cache.set(cache_key, response)

                return jsonify(response)

            except Exception as e:
                logger.error(f"Error in get_comparison_matrix: {e}")
                return jsonify({"error": str(e)}), 500

        @bp.route("/health", methods=["GET"])
        def health_check():
            """Health check endpoint."""
            try:
                cursor = self.db.conn.cursor()
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
        """
        Initialize cache.

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
