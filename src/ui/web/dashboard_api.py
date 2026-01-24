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
