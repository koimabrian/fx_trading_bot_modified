"""Web-based dashboard server for the FX Trading Bot.

Provides interactive backtesting results visualization with dynamic filtering,
equity curve viewing, and optimization heatmap analysis via a browser interface.
All data loaded from the backtest database in real-time.
"""

import json
import logging
import math
import os
from flask import Flask, render_template, jsonify, request, send_file
from flask_cors import CORS
from src.database.db_manager import DatabaseManager


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
        self.logger = logging.getLogger(__name__)

        # Create Flask app with absolute paths
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        template_dir = os.path.join(base_dir, "ui", "web", "templates")
        static_dir = os.path.join(base_dir, "ui", "web", "static")

        self.app = Flask(
            __name__, template_folder=template_dir, static_folder=static_dir
        )
        CORS(self.app)

        # Register routes
        self.app.add_url_rule("/", "index", self.index)
        self.app.add_url_rule("/api/symbols", "api_symbols", self.api_symbols)
        self.app.add_url_rule("/api/timeframes", "api_timeframes", self.api_timeframes)
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
        self.app.add_url_rule(
            "/view-equity-curve", "view_equity_curve", self.view_equity_curve
        )
        self.app.add_url_rule("/view-heatmap", "view_heatmap", self.view_heatmap)
        self.app.add_url_rule(
            "/api/comparison", "api_comparison", self.api_comparison, methods=["GET"]
        )

    def _get_db(self):
        """Get a fresh database connection for the current request thread.

        Returns:
            DatabaseManager: New connection instance for thread-safe operations
        """
        return DatabaseManager(self.config)

    def index(self):
        """Serve the main dashboard HTML."""
        return render_template("dashboard.html")

    def api_symbols(self):
        """Get available symbols from database."""
        try:
            with self._get_db() as db:
                symbols_result = db.execute_query(
                    "SELECT DISTINCT symbol FROM backtest_backtests ORDER BY symbol"
                )
                symbols = [row["symbol"] for row in symbols_result]
            return jsonify({"symbols": symbols, "status": "success"})
        except (RuntimeError, ValueError, KeyError) as e:
            self.logger.error("Failed to fetch symbols: %s", e)
            return jsonify({"symbols": [], "status": "error", "message": str(e)}), 500

    def api_timeframes(self):
        """Get available timeframes from database."""
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

    @staticmethod
    def _timeframe_to_string(timeframe):
        """Convert numeric timeframe to string format.

        Args:
            timeframe: Numeric timeframe (15, 60, 240) or string

        Returns:
            String format (M15, H1, H4)
        """
        timeframe_map = {
            15: "M15",
            "15": "M15",
            60: "H1",
            "60": "H1",
            240: "H4",
            "240": "H4",
        }
        return timeframe_map.get(timeframe, str(timeframe))

    @staticmethod
    def _safe_round(value, decimals=2):
        """Safely round a value, handling NaN and None.

        Args:
            value: Value to round
            decimals: Number of decimal places

        Returns:
            Rounded number, 0 if NaN/None, or original value if not numeric
        """
        if value is None:
            return 0
        try:
            if math.isnan(value):
                return 0
            return round(value, decimals)
        except (TypeError, ValueError):
            return 0

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
                SELECT b.strategy_id, s.name AS strategy_name, b.symbol, b.timeframe, b.metrics
                FROM backtest_backtests b
                JOIN backtest_strategies s ON b.strategy_id = s.id
                WHERE (:symbol = 'All' OR b.symbol = :symbol)
                AND (:timeframe = 'All' OR b.timeframe = :timeframe)
                ORDER BY b.symbol, b.timeframe
            """

            with self._get_db() as db:
                results = db.execute_query(
                    query, {"symbol": symbol, "timeframe": timeframe}
                )

                # Convert results to serializable format, handling NaN values
                formatted_results = []
                for row in results:
                    metrics = json.loads(row["metrics"]) if row["metrics"] else {}
                    formatted_results.append(
                        {
                            "strategy": row["strategy_name"],
                            "symbol": row["symbol"],
                            "timeframe": row["timeframe"],
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

    def run(self, debug=False):
        """Start the dashboard server."""
        self.logger.info(
            "Starting FX Trading Bot Dashboard on http://%s:%d", self.host, self.port
        )
        print(f"\n[OK] Dashboard available at: http://{self.host}:{self.port}\n")
        self.app.run(host=self.host, port=self.port, debug=debug)
