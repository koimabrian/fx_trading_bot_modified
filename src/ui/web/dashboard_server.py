"""Web-based dashboard server for the FX Trading Bot.

Provides interactive backtesting results visualization with dynamic filtering,
equity curve viewing, and optimization heatmap analysis via a browser interface.
All data loaded from the backtest database in real-time.
"""

import json
import math
import os
import time

import MetaTrader5 as mt5
from flask import Flask, jsonify, render_template, request, send_file
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS

from src.database.db_manager import DatabaseManager
from src.reports.report_generator import ReportGenerator
from src.ui.web.dashboard_api import DashboardAPI
from src.ui.web.live_broadcaster import broadcaster
from src.utils.logging_factory import LoggingFactory
from src.utils.timeframe_utils import format_timeframe


class SafeJSONProvider(DefaultJSONProvider):
    """Custom JSON encoder that converts NaN and Infinity to 0."""

    def default(self, o):
        if isinstance(o, float):
            if math.isnan(o) or math.isinf(o):
                return 0
        return super().default(o)


class DashboardServer:
    """Flask-based web dashboard for the FX Trading Bot."""

    def __init__(self, config, host="127.0.0.1", port=5000):
        """Initialize the web dashboard server.

        Args:
            config: Configuration dictionary
            host: Host to bind to (default: 127.0.0.1)
            port: Port to listen on (default: 5000)
        """
        self.config = config
        self.host = host
        self.port = port
        self.logger = LoggingFactory.get_logger(__name__)

        # Create Flask app with absolute paths
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        template_dir = os.path.join(base_dir, "ui", "web", "templates")
        static_dir = os.path.join(base_dir, "ui", "web", "static")

        self.app = Flask(
            __name__, template_folder=template_dir, static_folder=static_dir
        )
        # Use custom JSON provider to handle NaN and Infinity
        self.app.json = SafeJSONProvider(self.app)
        CORS(self.app)

        # Initialize Socket.IO for live updates
        self.socketio = broadcaster.init_socketio(self.app)

        # Initialize database and report API
        self.db = DatabaseManager(config)
        self.db.connect()

        # Register routes
        self.app.add_url_rule("/", "index", self.index)
        self.app.add_url_rule("/api/symbols", "api_symbols", self.api_symbols)
        self.app.add_url_rule("/api/timeframes", "api_timeframes", self.api_timeframes)
        self.app.add_url_rule("/api/categories", "api_categories", self.api_categories)
        self.app.add_url_rule(
            "/api/results", "api_results", self.api_results, methods=["GET"]
        )
        self.app.add_url_rule(
            "/api/equity-curve/<symbol>/<strategy>",
            "api_equity_curve",
            self.api_equity_curve,
        )
        self.app.add_url_rule(
            "/api/heatmap/<symbol>/<timeframe>", "api_heatmap", self.api_heatmap
        )

        # Register Phase 3 report API routes
        self._register_report_routes()
        self.app.add_url_rule(
            "/view-equity-curve", "view_equity_curve", self.view_equity_curve
        )
        self.app.add_url_rule("/view-heatmap", "view_heatmap", self.view_heatmap)
        self.app.add_url_rule(
            "/api/comparison", "api_comparison", self.api_comparison, methods=["GET"]
        )

        # Optimal parameters endpoint
        self.app.add_url_rule(
            "/api/optimal-parameters",
            "api_optimal_parameters",
            self.api_optimal_parameters,
            methods=["GET"],
        )

        # Trading pairs status endpoint
        self.app.add_url_rule(
            "/api/trading-pairs",
            "api_trading_pairs",
            self.api_trading_pairs,
            methods=["GET"],
        )

        # Live trading statistics endpoint
        self.app.add_url_rule(
            "/api/live-statistics",
            "api_live_statistics",
            self.api_live_statistics,
            methods=["GET"],
        )

        # Clear execution history endpoint
        self.app.add_url_rule(
            "/api/clear-execution-history",
            "api_clear_execution_history",
            self.api_clear_execution_history,
            methods=["POST"],
        )

        # Live data endpoint (for unified dashboard)
        self.app.add_url_rule(
            "/api/live-data",
            "api_live_data",
            self.api_live_data,
            methods=["GET"],
        )

        # Register DashboardAPI blueprint for additional report endpoints
        dashboard_api = DashboardAPI(self.db, config)
        self.app.register_blueprint(dashboard_api.blueprint)

    def _get_db(self):
        """Get a fresh database connection for the current request thread.

        Returns:
            DatabaseManager: New connection instance for thread-safe operations
        """
        db = DatabaseManager(self.config)
        db.connect()
        return db

    def index(self):
        """Serve the main dashboard HTML page.

        Returns:
            Rendered dashboard_unified.html template.
        """
        return render_template("dashboard_unified.html")

    def api_symbols(self):
        """Get available symbols from database.

        Returns:
            JSON response with list of symbols and status.
        """
        try:
            with self._get_db() as db:
                symbols_result = db.execute_query(
                    "SELECT DISTINCT tp.symbol FROM backtest_backtests b JOIN tradable_pairs tp ON b.symbol_id = tp.id ORDER BY tp.symbol"
                ).fetchall()
                symbols = [row[0] for row in symbols_result]
            return jsonify({"symbols": symbols, "status": "success"})
        except (RuntimeError, ValueError, KeyError) as e:
            self.logger.error("Failed to fetch symbols: %s", e)
            return jsonify({"symbols": [], "status": "error", "message": str(e)}), 500

    def api_timeframes(self):
        """Get available timeframes from database.

        Returns:
            JSON response with list of timeframes and status.
        """
        try:
            with self._get_db() as db:
                timeframes_result = db.execute_query(
                    "SELECT DISTINCT timeframe FROM backtest_backtests ORDER BY timeframe"
                )
                timeframes = [row["timeframe"] for row in timeframes_result]
            return jsonify({"timeframes": timeframes, "status": "success"})
        except (RuntimeError, ValueError, KeyError) as e:
            self.logger.error("Failed to fetch timeframes: %s", e)
            return (
                jsonify({"timeframes": [], "status": "error", "message": str(e)}),
                500,
            )

    def api_categories(self):
        """Get available symbol categories from database with symbol counts.

        Returns:
            JSON response with category list, counts, and status.
        """
        try:
            with self._get_db() as db:
                # Query categories with symbol counts
                categories_result = db.execute_query(
                    """SELECT category, COUNT(*) as symbol_count 
                       FROM tradable_pairs 
                       WHERE category IS NOT NULL AND category != 'unknown'
                       GROUP BY category 
                       ORDER BY symbol_count DESC, category"""
                ).fetchall()

                # Convert to list of dicts with label and count
                categories = [
                    {
                        "category": row["category"],
                        "count": row["symbol_count"],
                        "label": f"{row['category'].title()} ({row['symbol_count']})",
                    }
                    for row in categories_result
                ]

            self.logger.debug(f"Loaded categories: {categories}")
            return jsonify({"categories": categories, "status": "success"})
        except (RuntimeError, ValueError, KeyError) as e:
            self.logger.error("Failed to fetch categories: %s", e)
            return (
                jsonify({"categories": [], "status": "error", "message": str(e)}),
                500,
            )

    @staticmethod
    def _timeframe_to_string(timeframe):
        """Convert numeric timeframe to string format.

        Delegates to shared utility function.
        See src.utils.timeframe_utils.format_timeframe for details.

        Args:
            timeframe: Numeric timeframe (15, 60, 240) or string

        Returns:
            String format (M15, H1, H4)
        """
        return format_timeframe(timeframe)

    @staticmethod
    def _safe_round(value, decimals=2):
        """Safely round a value, handling NaN, Infinity, and None.

        Args:
            value: Value to round
            decimals: Number of decimal places

        Returns:
            Rounded number, 0 if NaN/Infinity/None, or original value if not numeric
        """
        if value is None:
            return 0
        try:
            if math.isnan(value) or math.isinf(value):
                return 0
            return round(value, decimals)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _clean_metrics(metrics_dict):
        """Clean all metrics to ensure they're JSON-serializable.

        Converts NaN and Infinity to 0, and ensures all values are valid JSON.

        Args:
            metrics_dict: Dictionary of metrics from backtest results

        Returns:
            Cleaned dictionary with valid JSON values
        """
        if not metrics_dict:
            return {}

        cleaned = {}
        for key, value in metrics_dict.items():
            if value is None:
                cleaned[key] = 0
            elif isinstance(value, float):
                if math.isnan(value) or math.isinf(value):
                    cleaned[key] = 0
                else:
                    cleaned[key] = value
            else:
                try:
                    # Try to convert to float and check again
                    float_val = float(value)
                    if math.isnan(float_val) or math.isinf(float_val):
                        cleaned[key] = 0
                    else:
                        cleaned[key] = value
                except (TypeError, ValueError):
                    # Not numeric, keep as-is
                    cleaned[key] = value

        return cleaned

    def api_results(self):
        """Get backtest results with optional filtering.

        Routes:
            GET /api/results?symbol=BTCUSD&timeframe=15

        Query Parameters:
            symbol: Filter by symbol (default: 'All')
            timeframe: Filter by timeframe in minutes (default: 'All')

        Returns:
            JSON with backtest results and metrics (all NaN values converted to 0)
        """
        try:
            symbol = request.args.get("symbol", "All")
            timeframe = request.args.get("timeframe", "All")

            query = """
                SELECT b.strategy_id, s.name AS strategy_name, tp.symbol, b.timeframe, b.metrics
                FROM backtest_backtests b
                JOIN backtest_strategies s ON b.strategy_id = s.id
                JOIN tradable_pairs tp ON b.symbol_id = tp.id
                WHERE (:symbol = 'All' OR tp.symbol = :symbol)
                AND (:timeframe = 'All' OR b.timeframe = :timeframe)
                ORDER BY tp.symbol, b.timeframe
            """

            with self._get_db() as db:
                results = db.execute_query(
                    query, {"symbol": symbol, "timeframe": timeframe}
                ).fetchall()

                # Convert results to serializable format, handling NaN values
                formatted_results = []
                for row in results:
                    metrics = json.loads(row[4]) if row[4] else {}
                    # Clean all metrics to remove NaN/Infinity
                    metrics = self._clean_metrics(metrics)
                    formatted_results.append(
                        {
                            "strategy_name": row[1],
                            "symbol": row[2],
                            "timeframe": row[3],
                            "total_return": self._safe_round(
                                metrics.get("total_return", 0), 2
                            ),
                            "total_trades": int(metrics.get("total_trades", 0)),
                            "win_rate": self._safe_round(metrics.get("win_rate", 0), 2),
                            "max_drawdown": self._safe_round(
                                metrics.get("max_drawdown", 0), 2
                            ),
                            "sharpe_ratio": self._safe_round(
                                metrics.get("sharpe_ratio", 0), 2
                            ),
                            "sortino_ratio": self._safe_round(
                                metrics.get("sortino_ratio", 0), 2
                            ),
                            "profit_factor": self._safe_round(
                                metrics.get("profit_factor", 0), 2
                            ),
                            "calmar_ratio": self._safe_round(
                                metrics.get("calmar_ratio", 0), 2
                            ),
                            "ulcer_index": self._safe_round(
                                metrics.get("ulcer_index", 0), 2
                            ),
                            "k_ratio": self._safe_round(metrics.get("k_ratio", 0), 2),
                            "tail_ratio": self._safe_round(
                                metrics.get("tail_ratio", 0), 2
                            ),
                            "expectancy": self._safe_round(
                                metrics.get("expectancy", 0), 2
                            ),
                            "roe": self._safe_round(metrics.get("roe", 0), 2),
                            "time_to_recover": metrics.get("time_to_recover", "N/A"),
                        }
                    )

                self.logger.debug("Fetched %d backtest results", len(formatted_results))
                return jsonify({"results": formatted_results, "status": "success"})

        except (RuntimeError, ValueError, KeyError) as e:
            self.logger.error("Failed to fetch results: %s", e)
            return jsonify({"results": [], "status": "error", "message": str(e)}), 500

    def api_optimal_parameters(self):
        """Get optimal parameters from database.

        Returns:
            JSON with optimal parameters grouped by strategy
        """
        try:
            with self._get_db() as db:
                # Query optimal parameters with symbol JOIN
                query = """
                    SELECT tp.symbol, op.timeframe, op.strategy_name, 
                           op.parameter_value, op.metrics, op.last_optimized
                    FROM optimal_parameters op
                    JOIN tradable_pairs tp ON op.symbol_id = tp.id
                    ORDER BY op.strategy_name, tp.symbol, op.timeframe
                """
                results = db.execute_query(query).fetchall()

                # Group by strategy
                parameters_by_strategy = {}
                for row in results:
                    (
                        symbol,
                        timeframe,
                        strategy_name,
                        params_json,
                        metrics_json,
                        last_optimized,
                    ) = row

                    if strategy_name not in parameters_by_strategy:
                        parameters_by_strategy[strategy_name] = []

                    params = json.loads(params_json) if params_json else {}
                    metrics = json.loads(metrics_json) if metrics_json else {}
                    metrics = self._clean_metrics(metrics)

                    parameters_by_strategy[strategy_name].append(
                        {
                            "symbol": symbol,
                            "timeframe": self._timeframe_to_string(timeframe),
                            "parameters": params,
                            "metrics": {
                                "total_return": self._safe_round(
                                    metrics.get("total_return", 0), 2
                                ),
                                "total_trades": int(metrics.get("total_trades", 0)),
                                "win_rate": self._safe_round(
                                    metrics.get("win_rate", 0), 2
                                ),
                                "max_drawdown": self._safe_round(
                                    metrics.get("max_drawdown", 0), 2
                                ),
                                "sharpe_ratio": self._safe_round(
                                    metrics.get("sharpe_ratio", 0), 2
                                ),
                                "profit_factor": self._safe_round(
                                    metrics.get("profit_factor", 0), 2
                                ),
                            },
                            "last_optimized": last_optimized,
                        }
                    )

                self.logger.debug(
                    "Fetched optimal parameters for %d strategies",
                    len(parameters_by_strategy),
                )
                return jsonify(
                    {
                        "parameters": parameters_by_strategy,
                        "status": "success",
                        "total_sets": sum(
                            len(v) for v in parameters_by_strategy.values()
                        ),
                    }
                )

        except (RuntimeError, ValueError, KeyError, OSError) as e:
            self.logger.error("Failed to fetch optimal parameters: %s", e)
            return (
                jsonify({"parameters": {}, "status": "error", "message": str(e)}),
                500,
            )

    def api_trading_pairs(self):
        """Get list of trading pairs and their status.

        Returns:
            JSON with trading pairs and their configuration
        """
        try:
            with self._get_db() as db:
                # Query all tradable pairs with data count
                query = """
                    SELECT DISTINCT tp.symbol, COUNT(md.id) as data_points,
                           MAX(md.time) as last_update
                    FROM tradable_pairs tp
                    LEFT JOIN market_data md ON tp.id = md.symbol_id
                    GROUP BY tp.symbol
                    ORDER BY tp.symbol
                """
                results = db.execute_query(query).fetchall()

                pairs = []
                for row in results:
                    symbol, data_points, last_update = row
                    pairs.append(
                        {
                            "symbol": symbol,
                            "data_points": int(data_points) if data_points else 0,
                            "last_update": last_update,
                            "has_data": int(data_points) > 0 if data_points else False,
                        }
                    )

                self.logger.debug(
                    "Fetched trading pairs: %d pairs configured",
                    len(pairs),
                )
                return jsonify(
                    {
                        "pairs": pairs,
                        "status": "success",
                        "total_pairs": len(pairs),
                    }
                )

        except (RuntimeError, ValueError, KeyError, OSError) as e:
            self.logger.error("Failed to fetch trading pairs: %s", e)
            return (
                jsonify({"pairs": [], "status": "error", "message": str(e)}),
                500,
            )

    def api_live_statistics(self):
        """Get live trading statistics and recent trades.

        Returns:
            JSON with live trading stats including trades, P&L, signals
        """
        try:
            with self._get_db() as db:
                # Get recent trades (last 24 hours)
                trades_query = """
                    SELECT symbol, action, entry_price, exit_price, volume, 
                           strategy, status, created_at, 
                           CASE WHEN exit_price IS NOT NULL 
                                THEN ((exit_price - entry_price) * volume)
                                ELSE 0 
                           END as pnl
                    FROM trades
                    WHERE created_at >= datetime('now', '-1 day')
                    ORDER BY created_at DESC
                    LIMIT 100
                """
                trades_result = db.execute_query(trades_query).fetchall()
                trades = [dict(row) for row in trades_result] if trades_result else []

                # Calculate statistics
                total_trades = len(trades)
                executed_trades = [
                    t for t in trades if t.get("status") in ["executed", "closed"]
                ]
                pending_trades = [
                    t
                    for t in trades
                    if t.get("status") in ["pending", "signal_generated"]
                ]

                total_pnl = sum(t.get("pnl", 0) for t in executed_trades)
                winning_trades = len(
                    [t for t in executed_trades if t.get("pnl", 0) > 0]
                )
                losing_trades = len([t for t in executed_trades if t.get("pnl", 0) < 0])

                win_rate = (
                    (winning_trades / len(executed_trades) * 100)
                    if executed_trades
                    else 0
                )
                avg_pnl = (total_pnl / len(executed_trades)) if executed_trades else 0

                # Get active positions
                active_query = """
                    SELECT tp.symbol, t.trade_type as action, t.open_price as entry_price, t.volume, t.strategy_name as strategy
                    FROM trades t
                    JOIN tradable_pairs tp ON t.symbol_id = tp.id
                    WHERE t.status IN ('executed', 'open')
                    ORDER BY t.open_time DESC
                """
                active_result = db.execute_query(active_query).fetchall()
                active_positions = (
                    [dict(row) for row in active_result] if active_result else []
                )

                # Also get live positions from MT5
                try:  # pylint: disable=no-member
                    if mt5.initialize():
                        mt5_positions = mt5.positions_get()
                        if mt5_positions:
                            for pos in mt5_positions:
                                active_positions.append(
                                    {
                                        "symbol": pos.symbol,
                                        "action": "buy" if pos.type == 0 else "sell",
                                        "entry_price": pos.price_open,
                                        "volume": pos.volume,
                                        "strategy": "MT5 Live",
                                    }
                                )
                        mt5.shutdown()
                except (RuntimeError, OSError, AttributeError) as e:
                    self.logger.debug("Could not fetch MT5 positions: %s", e)

                self.logger.debug(
                    "Live statistics: %d total trades, %d executed, %d pending",
                    total_trades,
                    len(executed_trades),
                    len(pending_trades),
                )

                return jsonify(
                    {
                        "status": "success",
                        "summary": {
                            "total_trades": total_trades,
                            "executed_trades": len(executed_trades),
                            "pending_trades": len(pending_trades),
                            "total_pnl": self._safe_round(total_pnl, 2),
                            "winning_trades": winning_trades,
                            "losing_trades": losing_trades,
                            "win_rate": self._safe_round(win_rate, 2),
                            "avg_pnl_per_trade": self._safe_round(avg_pnl, 2),
                        },
                        "recent_trades": trades,
                        "active_positions": active_positions,
                        "timestamp": time.time(),
                    }
                )

        except (RuntimeError, ValueError, KeyError, OSError) as e:
            self.logger.error("Failed to fetch live statistics: %s", e)
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": str(e),
                        "summary": {
                            "total_trades": 0,
                            "executed_trades": 0,
                            "pending_trades": 0,
                            "total_pnl": 0,
                            "win_rate": 0,
                        },
                        "recent_trades": [],
                        "active_positions": [],
                    }
                ),
                500,
            )

    def api_clear_execution_history(self):
        """Clear the trade execution history.

        Returns:
            JSON with success/error status
        """
        try:
            with self._get_db() as db:
                # Delete all trades from the database
                delete_query = "DELETE FROM trades"
                db.execute_query(delete_query)
                db.conn.commit()

                self.logger.info("Execution history cleared")

                return jsonify(
                    {"status": "success", "message": "Execution history cleared"}
                )

        except Exception as e:
            self.logger.error("Failed to clear execution history: %s", e)
            return (
                jsonify({"status": "error", "message": str(e)}),
                500,
            )

    def api_live_data(self):
        """Get live trading data for the unified dashboard.

        Returns:
            JSON with live trading info, signals, positions, and execution summary
        """
        try:
            with self._get_db() as db:
                # Get recent signals (last 10)
                signals_query = """
                    SELECT tp.symbol, t.trade_type as action, 0.0 as entry_price, 
                           t.strategy_name, t.timeframe, t.status, t.open_time as timestamp,
                           json_object('name', t.strategy_name, 'confidence', 0.5) as strategy_info
                    FROM trades t
                    JOIN tradable_pairs tp ON t.symbol_id = tp.id
                    WHERE t.status = 'signal_generated'
                    ORDER BY t.open_time DESC
                    LIMIT 10
                """
                signals_result = db.execute_query(signals_query).fetchall()
                signals = []
                if signals_result:
                    for row in signals_result:
                        signal = dict(row)
                        # Parse strategy_info if it's a JSON string
                        if isinstance(signal.get("strategy_info"), str):
                            try:
                                signal["strategy_info"] = json.loads(
                                    signal["strategy_info"]
                                )
                            except (ValueError, TypeError) as e:
                                self.logger.debug(
                                    "Failed to parse strategy_info JSON: %s", e
                                )
                                signal["strategy_info"] = {
                                    "name": signal.get("strategy_name", "N/A"),
                                    "confidence": 0.5,
                                }
                        signals.append(signal)

                # Get open/active positions from database
                positions_query = """
                    SELECT tp.symbol, t.trade_type as side, t.open_price as entry_price,
                           t.open_price as current_price,
                           COALESCE(t.profit, 0) as pnl,
                           t.volume
                    FROM trades t
                    JOIN tradable_pairs tp ON t.symbol_id = tp.id
                    WHERE t.status IN ('executed', 'open')
                    ORDER BY t.open_time DESC
                """
                positions_result = db.execute_query(positions_query).fetchall()
                positions = (
                    [dict(row) for row in positions_result] if positions_result else []
                )

                # Also get live positions from MT5
                mt5_positions_list = []
                try:
                    if mt5.initialize():
                        mt5_positions = mt5.positions_get()
                        if mt5_positions:
                            for pos in mt5_positions:
                                mt5_pos = {
                                    "symbol": pos.symbol,
                                    "side": "buy" if pos.type == 0 else "sell",
                                    "entry_price": pos.price_open,
                                    "current_price": pos.price_current,
                                    "pnl": pos.profit,
                                    "volume": pos.volume,
                                }
                                positions.append(mt5_pos)
                                mt5_positions_list.append(mt5_pos)
                        mt5.shutdown()
                except (RuntimeError, OSError, AttributeError) as e:
                    self.logger.debug("Could not fetch MT5 positions: %s", e)

                # Get recent executed trades (last 5)
                trades_query = """
                    SELECT tp.symbol, t.trade_type as action, t.strategy_name,
                           t.status, t.open_time as timestamp
                    FROM trades t
                    JOIN tradable_pairs tp ON t.symbol_id = tp.id
                    WHERE t.status IN ('executed', 'closed')
                    ORDER BY t.open_time DESC
                    LIMIT 5
                """
                trades_result = db.execute_query(trades_query).fetchall()
                recent_trades = (
                    [dict(row) for row in trades_result] if trades_result else []
                )

                # Calculate live statistics - ALL trades (not just last 24h)
                stats_query = """
                    SELECT 
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN status = 'executed' THEN 1 ELSE 0 END) as executed,
                        SUM(CASE WHEN close_time IS NULL THEN 1 ELSE 0 END) as open_count,
                        SUM(CASE WHEN close_time IS NOT NULL AND profit IS NOT NULL THEN profit ELSE 0 END) as realized_profit,
                        SUM(CASE WHEN close_time IS NOT NULL AND profit > 0 THEN 1 ELSE 0 END) as winning_trades,
                        SUM(CASE WHEN close_time IS NOT NULL AND profit < 0 THEN 1 ELSE 0 END) as losing_trades,
                        SUM(CASE WHEN close_time IS NOT NULL THEN 1 ELSE 0 END) as closed_trades
                    FROM trades
                """
                stats_result = db.execute_query(stats_query).fetchone()

                # Calculate unrealized P&L from MT5 live positions only
                unrealized_profit = sum(
                    [
                        pos.get("pnl", 0)
                        for pos in mt5_positions_list
                        if isinstance(pos, dict)
                    ]
                )

                # Count only MT5 live positions (the actual real-time positions)
                # Database records are historical, MT5 has the live positions
                open_positions_count = len(mt5_positions_list)

                # Calculate total profit (realized + unrealized)
                realized_profit = 0
                if stats_result:
                    try:
                        realized_profit = stats_result["realized_profit"] or 0
                    except (KeyError, TypeError):
                        realized_profit = 0
                total_profit = realized_profit + unrealized_profit

                # Calculate win rate from closed trades
                closed_trades = 0
                winning_trades = 0
                if stats_result:
                    try:
                        closed_trades = stats_result["closed_trades"] or 0
                        winning_trades = stats_result["winning_trades"] or 0
                    except (KeyError, TypeError):
                        closed_trades = 0
                        winning_trades = 0

                win_rate = (
                    (winning_trades / closed_trades * 100) if closed_trades > 0 else 0.0
                )

                total_trades = 0
                if stats_result:
                    try:
                        total_trades = stats_result["total_trades"] or 0
                    except (KeyError, TypeError):
                        total_trades = 0

                stats = {
                    "net_profit": self._safe_round(total_profit, 2),
                    "win_rate": self._safe_round(win_rate, 2),
                    "total_trades": total_trades,
                    "open_positions": open_positions_count,
                    "net_profit_change": 0.0,
                }

                return jsonify(
                    {
                        "status": "success",
                        "statistics": stats,
                        "recent_signals": signals,
                        "open_positions": positions,
                        "recent_trades": recent_trades,
                        "equity_curve": {"timestamps": [], "values": []},
                        "timestamp": time.time(),
                    }
                )

        except (RuntimeError, ValueError, KeyError, OSError) as e:
            self.logger.error("Failed to fetch live data: %s", e)
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": str(e),
                        "statistics": {
                            "net_profit": 0,
                            "win_rate": 0,
                            "total_trades": 0,
                            "open_positions": 0,
                        },
                        "recent_signals": [],
                        "open_positions": [],
                        "recent_trades": [],
                        "equity_curve": {"timestamps": [], "values": []},
                    }
                ),
                500,
            )

    def api_equity_curve(self, symbol, strategy):
        """Get equity curve file path for symbol and strategy."""
        try:
            results_dir = "backtests/results"
            equity_file = os.path.abspath(
                f"{results_dir}/equity_curve_{symbol}_{strategy}.html"
            )

            if os.path.exists(equity_file):
                return jsonify(
                    {
                        "file": equity_file,
                        "filename": os.path.basename(equity_file),
                        "status": "success",
                    }
                )

            # Fallback: search for any available equity curve
            if os.path.exists(results_dir):
                files = [
                    f
                    for f in os.listdir(results_dir)
                    if f.startswith(f"equity_curve_{symbol}") and f.endswith(".html")
                ]
                if files:
                    fallback_file = os.path.abspath(os.path.join(results_dir, files[0]))
                    return jsonify(
                        {
                            "file": fallback_file,
                            "filename": os.path.basename(fallback_file),
                            "status": "success",
                            "warning": "Using fallback equity curve",
                        }
                    )

            return (
                jsonify(
                    {
                        "file": None,
                        "status": "error",
                        "message": f"No equity curve found for {symbol} ({strategy})",
                    }
                ),
                404,
            )

        except (RuntimeError, OSError, ValueError) as e:
            self.logger.error("Failed to get equity curve: %s", e)
            return jsonify({"file": None, "status": "error", "message": str(e)}), 500

    def api_heatmap(self, symbol, timeframe):
        """Get heatmap file path for symbol and timeframe.

        Converts numeric timeframe (15/60/240) to string format (M15/H1/H4).
        """
        try:
            # Convert numeric timeframe to string format (15 -> M15, 60 -> H1, 240 -> H4)
            timeframe_str = self._timeframe_to_string(timeframe)

            results_dir = "backtests/results"
            # Try both numeric and string formats
            heatmap_patterns = [
                f"{results_dir}/rsi_optimization_heatmap_{symbol}_{timeframe_str}.png",
                f"{results_dir}/macd_optimization_heatmap_{symbol}_{timeframe_str}.png",
                f"{results_dir}/rsi_optimization_heatmap_{symbol}_{timeframe}.png",
                f"{results_dir}/macd_optimization_heatmap_{symbol}_{timeframe}.png",
            ]

            # Check each pattern
            for heatmap_file in heatmap_patterns:
                if os.path.exists(heatmap_file):
                    return jsonify(
                        {
                            "file": os.path.abspath(heatmap_file),
                            "filename": os.path.basename(heatmap_file),
                            "status": "success",
                        }
                    )

            # Fallback: search for any available heatmap
            if os.path.exists(results_dir):
                files = [
                    f
                    for f in os.listdir(results_dir)
                    if (
                        f"optimization_heatmap_{symbol}_{timeframe_str}" in f
                        or f"optimization_heatmap_{symbol}_{timeframe}" in f
                    )
                ]
                if files:
                    fallback_file = os.path.abspath(os.path.join(results_dir, files[0]))
                    return jsonify(
                        {
                            "file": fallback_file,
                            "filename": os.path.basename(fallback_file),
                            "status": "success",
                            "warning": "Using fallback heatmap",
                        }
                    )

            return (
                jsonify(
                    {
                        "file": None,
                        "status": "error",
                        "message": f"No heatmap found for {symbol} ({timeframe_str})",
                    }
                ),
                404,
            )

        except (RuntimeError, OSError, ValueError) as e:
            self.logger.error("Failed to get heatmap: %s", e)
            return jsonify({"file": None, "status": "error", "message": str(e)}), 500

    def view_equity_curve(self):
        """Serve equity curve HTML file."""
        try:
            symbol = request.args.get("symbol")
            strategy = request.args.get("strategy")

            if not symbol or not strategy:
                return "Missing symbol or strategy parameter", 400

            results_dir = "backtests/results"
            equity_file = os.path.abspath(
                f"{results_dir}/equity_curve_{symbol}_{strategy}.html"
            )

            if os.path.exists(equity_file):
                return send_file(equity_file)

            # Fallback
            if os.path.exists(results_dir):
                files = [
                    f
                    for f in os.listdir(results_dir)
                    if f.startswith(f"equity_curve_{symbol}") and f.endswith(".html")
                ]
                if files:
                    fallback_file = os.path.abspath(os.path.join(results_dir, files[0]))
                    return send_file(fallback_file)

            return f"Equity curve not found for {symbol} ({strategy})", 404

        except (RuntimeError, OSError) as e:
            self.logger.error("Failed to serve equity curve: %s", e)
            return f"Error: {str(e)}", 500

    def view_heatmap(self):
        """Serve heatmap image file.

        Converts numeric timeframe (15/60/240) to string format (M15/H1/H4).
        """
        try:
            symbol = request.args.get("symbol")
            timeframe = request.args.get("timeframe")

            if not symbol or not timeframe:
                return "Missing symbol or timeframe parameter", 400

            # Convert numeric timeframe to string format
            timeframe_str = self._timeframe_to_string(timeframe)

            results_dir = "backtests/results"
            # Try both numeric and string formats
            heatmap_patterns = [
                f"{results_dir}/rsi_optimization_heatmap_{symbol}_{timeframe_str}.png",
                f"{results_dir}/macd_optimization_heatmap_{symbol}_{timeframe_str}.png",
                f"{results_dir}/rsi_optimization_heatmap_{symbol}_{timeframe}.png",
                f"{results_dir}/macd_optimization_heatmap_{symbol}_{timeframe}.png",
            ]

            for heatmap_file in heatmap_patterns:
                if os.path.exists(heatmap_file):
                    return send_file(heatmap_file, mimetype="image/png")

            # Fallback: search for any available heatmap
            if os.path.exists(results_dir):
                files = [
                    f
                    for f in os.listdir(results_dir)
                    if (
                        f"optimization_heatmap_{symbol}_{timeframe_str}" in f
                        or f"optimization_heatmap_{symbol}_{timeframe}" in f
                    )
                ]
                if files:
                    fallback_file = os.path.abspath(os.path.join(results_dir, files[0]))
                    return send_file(fallback_file, mimetype="image/png")

            return f"Heatmap not found for {symbol} ({timeframe_str})", 404

        except (RuntimeError, OSError) as e:
            self.logger.error("Failed to serve heatmap: %s", e)
            return f"Error: {str(e)}", 500

    def api_comparison(self):
        """Get comparison data for bar charts and metrics.

        Returns:
            JSON with comparison metrics for all strategies, symbols, and timeframes
        """
        try:
            symbol = request.args.get("symbol", "All")
            timeframe = request.args.get("timeframe", "All")

            query = """
                SELECT b.symbol, b.timeframe, s.name AS strategy_name, b.metrics
                FROM backtest_backtests b
                JOIN backtest_strategies s ON b.strategy_id = s.id
                WHERE (:symbol = 'All' OR b.symbol = :symbol)
                AND (:timeframe = 'All' OR b.timeframe = :timeframe)
                ORDER BY b.symbol, b.timeframe, s.name
            """

            with self._get_db() as db:
                results = db.execute_query(
                    query, {"symbol": symbol, "timeframe": timeframe}
                )

                # Group by symbol/timeframe for comparison
                comparison_data = []
                for row in results:
                    metrics = json.loads(row["metrics"]) if row["metrics"] else {}
                    comparison_data.append(
                        {
                            "symbol": row["symbol"],
                            "timeframe": row["timeframe"],
                            "strategy": row["strategy_name"],
                            "sharpe_ratio": self._safe_round(
                                metrics.get("sharpe_ratio", 0), 2
                            ),
                            "total_return_pct": self._safe_round(
                                metrics.get("total_return_pct", 0), 2
                            ),
                            "max_drawdown_pct": self._safe_round(
                                metrics.get("max_drawdown_pct", 0), 2
                            ),
                            "profit_factor": self._safe_round(
                                metrics.get("profit_factor", 0), 2
                            ),
                            "win_rate_pct": self._safe_round(
                                metrics.get("win_rate_pct", 0), 2
                            ),
                        }
                    )

                self.logger.debug("Fetched %d comparison records", len(comparison_data))
                return jsonify({"comparison": comparison_data, "status": "success"})

        except (RuntimeError, ValueError, KeyError) as e:
            self.logger.error("Failed to fetch comparison data: %s", e)
            return (
                jsonify({"comparison": [], "status": "error", "message": str(e)}),
                500,
            )

    def _register_report_routes(self):
        """Register Phase 3 report generation API routes."""
        report_gen = ReportGenerator(self.db, self.config)

        # Summary metrics endpoint
        @self.app.route("/api/reports/summary", methods=["GET"])
        def get_summary():
            try:
                summary = report_gen.get_summary_metrics()
                if summary is None:
                    return jsonify({"error": "No data found"}), 404
                return jsonify({"status": "success", "data": summary})
            except Exception as e:
                self.logger.error(f"Error in summary endpoint: {e}")
                return jsonify({"error": str(e)}), 500

        # Volatility ranking endpoint
        @self.app.route("/api/reports/volatility/<int:timeframe>", methods=["GET"])
        def get_volatility(timeframe):
            try:
                df = report_gen.generate_volatility_ranking(timeframe)
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
                self.logger.error(f"Error in volatility endpoint: {e}")
                return jsonify({"error": str(e)}), 500

        # Multi-symbol comparison endpoint
        @self.app.route("/api/reports/comparison/<int:timeframe>", methods=["GET"])
        def get_multi_comparison(timeframe):
            try:
                strategy = request.args.get("strategy", "rsi")
                df = report_gen.generate_multi_symbol_comparison(strategy, timeframe)
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
                self.logger.error(f"Error in comparison endpoint: {e}")
                return jsonify({"error": str(e)}), 500

        self.logger.info("Phase 3 report API routes registered")

    def run(self, debug=False):
        """Start the dashboard server."""
        self.logger.info(
            "Starting FX Trading Bot Dashboard on http://%s:%d", self.host, self.port
        )
        print(f"\n[OK] Dashboard available at: http://{self.host}:{self.port}\n")
        self.app.run(host=self.host, port=self.port, debug=debug)
