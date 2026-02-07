"""
Report generation engine for performance analysis.

Generates comprehensive reports from backtesting and live trading data:
- Strategy performance (single symbol/strategy/timeframe)
- Multi-symbol strategy comparison
- Volatility ranking and analysis
- Export formats (CSV, JSON, HTML)
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Optional

import pandas as pd

from src.database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate comprehensive performance reports from database."""

    def __init__(self, db: DatabaseManager, config: Dict):
        """
        Initialize report generator.

        Args:
            db: DatabaseManager instance
            config: Configuration dict with 'database', 'timeframes', 'pairs', etc.
        """
        self.db = db
        self.config = config
        self.logger = logger

    def generate_strategy_performance(
        self,
        symbol: str,
        strategy: str,
        timeframe: int,
    ) -> Optional[pd.DataFrame]:
        """
        Generate performance report for single strategy/symbol/timeframe.

        Args:
            symbol: Currency pair (e.g., 'EURUSD')
            strategy: Strategy name (e.g., 'rsi')
            timeframe: Timeframe in minutes (15, 60, 240, etc.)

        Returns:
            DataFrame with metrics: sharpe_ratio, total_return, win_rate, etc.
            None if no data found
        """
        try:
            cursor = self.db.conn.cursor()

            # Query backtest results for this strategy/symbol/timeframe
            query = """
                SELECT 
                    bb.sharpe_ratio,
                    bb.sortino_ratio,
                    bb.calmar_ratio,
                    bb.total_return,
                    bb.win_rate,
                    bb.profit_factor,
                    bb.max_drawdown,
                    bb.trades_total,
                    bb.trades_winning,
                    bb.avg_trade_return,
                    bb.params,
                    bb.start_date,
                    bb.end_date
                FROM backtest_backtests bb
                JOIN backtest_strategies bs ON bb.strategy_id = bs.id
                WHERE 
                    bs.name = ? 
                    AND bb.symbol = ?
                    AND bb.timeframe = ?
                ORDER BY bb.created_at DESC
                LIMIT 1
            """

            cursor.execute(query, (strategy, symbol, timeframe))
            result = cursor.fetchone()

            if not result:
                self.logger.warning(
                    f"No backtest data for {symbol}/{strategy}/{timeframe}min"
                )
                return None

            # Parse metrics
            metrics = {
                "symbol": symbol,
                "strategy": strategy,
                "timeframe": timeframe,
                "sharpe_ratio": result[0],
                "sortino_ratio": result[1],
                "calmar_ratio": result[2],
                "total_return": result[3],
                "win_rate": result[4],
                "profit_factor": result[5],
                "max_drawdown": result[6],
                "trades_total": result[7],
                "trades_winning": result[8],
                "avg_trade_return": result[9],
                "start_date": result[11],
                "end_date": result[12],
            }

            # Parse params JSON if available
            if result[10]:
                try:
                    metrics["params"] = json.loads(result[10])
                except (json.JSONDecodeError, TypeError):
                    metrics["params"] = {}

            return pd.DataFrame([metrics])

        except Exception as e:
            self.logger.error(f"Error generating strategy performance report: {e}")
            return None

    def generate_multi_symbol_comparison(
        self,
        strategy: str,
        timeframe: int,
    ) -> Optional[pd.DataFrame]:
        """
        Compare strategy performance across all symbols.

        Args:
            strategy: Strategy name
            timeframe: Timeframe in minutes

        Returns:
            DataFrame with all symbols ranked by Sharpe ratio
            Columns: symbol, sharpe_ratio, total_return, win_rate, max_drawdown, atr
            None if no data found
        """
        try:
            cursor = self.db.conn.cursor()

            # Query all symbols for strategy/timeframe, ranked by Sharpe
            query = """
                SELECT 
                    bb.symbol,
                    bs.name as strategy,
                    bb.timeframe,
                    bb.sharpe_ratio,
                    bb.total_return,
                    bb.win_rate,
                    bb.profit_factor,
                    bb.max_drawdown,
                    bb.trades_total
                FROM backtest_backtests bb
                JOIN backtest_strategies bs ON bb.strategy_id = bs.id
                WHERE 
                    bs.name = ?
                    AND bb.timeframe = ?
                ORDER BY bb.sharpe_ratio DESC
            """

            cursor.execute(query, (strategy, timeframe))
            results = cursor.fetchall()

            if not results:
                self.logger.warning(f"No comparison data for {strategy}/{timeframe}min")
                return None

            # Build DataFrame
            df_data = []
            for row in results:
                df_data.append(
                    {
                        "symbol": row[0],
                        "strategy": row[1],
                        "timeframe": row[2],
                        "sharpe_ratio": row[3],
                        "total_return": row[4],
                        "win_rate": row[5],
                        "profit_factor": row[6],
                        "max_drawdown": row[7],
                        "trades_total": row[8],
                    }
                )

            df = pd.DataFrame(df_data)

            # Add rank column
            df["rank"] = range(1, len(df) + 1)

            return df

        except Exception as e:
            self.logger.error(f"Error generating multi-symbol comparison: {e}")
            return None

    def generate_volatility_ranking(
        self,
        timeframe: int,
    ) -> Optional[pd.DataFrame]:
        """
        Rank symbols by volatility (ATR) at given timeframe.

        Args:
            timeframe: Timeframe in minutes

        Returns:
            DataFrame with symbols ranked by ATR (high to low)
            Columns: symbol, atr_value, volatility_level, rank
            None if no data found
        """
        try:
            cursor = self.db.conn.cursor()

            # Query ATR values from backtest results
            # ATR stored as JSON in metrics, extract and rank
            query = """
                SELECT 
                    bb.symbol,
                    bb.metrics
                FROM backtest_backtests bb
                WHERE bb.timeframe = ?
                ORDER BY bb.created_at DESC
            """

            cursor.execute(query, (timeframe,))
            results = cursor.fetchall()

            if not results:
                self.logger.warning(f"No volatility data for {timeframe}min")
                return None

            # Extract ATR values (latest per symbol)
            symbol_atr = {}
            for symbol, metrics_json in results:
                if symbol not in symbol_atr:  # Keep first (latest)
                    try:
                        metrics = json.loads(metrics_json) if metrics_json else {}
                        atr = metrics.get("atr", None)
                        if atr is not None:
                            symbol_atr[symbol] = float(atr)
                    except (json.JSONDecodeError, TypeError, ValueError):
                        pass

            if not symbol_atr:
                self.logger.warning("No ATR values found in metrics")
                return None

            # Sort by ATR (high to low)
            sorted_symbols = sorted(
                symbol_atr.items(), key=lambda x: x[1], reverse=True
            )

            # Build DataFrame with volatility levels
            df_data = []
            for rank, (symbol, atr_value) in enumerate(sorted_symbols, 1):
                # Volatility level: High (top 33%), Medium (mid 33%), Low (bottom 33%)
                percentile = rank / len(sorted_symbols)
                if percentile < 0.33:
                    volatility_level = "High"
                elif percentile < 0.67:
                    volatility_level = "Medium"
                else:
                    volatility_level = "Low"

                df_data.append(
                    {
                        "rank": rank,
                        "symbol": symbol,
                        "atr_value": round(atr_value, 5),
                        "volatility_level": volatility_level,
                    }
                )

            return pd.DataFrame(df_data)

        except Exception as e:
            self.logger.error(f"Error generating volatility ranking: {e}")
            return None

    def export_report(
        self,
        report_data: pd.DataFrame,
        format: str = "csv",
        filename: Optional[str] = None,
    ) -> Optional[str]:
        """
        Export report in specified format.

        Args:
            report_data: DataFrame to export
            format: 'csv', 'json', or 'html'
            filename: Optional filename (auto-generated if None)

        Returns:
            Filename of exported report, None if error
        """
        try:
            # Generate filename if not provided
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"report_{timestamp}.{format}"

            # Ensure reports directory exists
            reports_dir = "backtests/results"
            os.makedirs(reports_dir, exist_ok=True)

            filepath = os.path.join(reports_dir, filename)

            # Export based on format
            if format.lower() == "csv":
                report_data.to_csv(filepath, index=False)
                self.logger.info(f"Report exported to CSV: {filepath}")

            elif format.lower() == "json":
                report_data.to_json(filepath, orient="records", indent=2)
                self.logger.info(f"Report exported to JSON: {filepath}")

            elif format.lower() == "html":
                # Create nice HTML table
                html = report_data.to_html(index=False, classes="report-table")
                html = f"""
                <html>
                <head>
                    <title>Trading Report</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 20px; }}
                        .report-table {{ border-collapse: collapse; width: 100%; }}
                        .report-table th {{ background-color: #4CAF50; color: white; padding: 10px; text-align: left; }}
                        .report-table td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
                        .report-table tr:hover {{ background-color: #f5f5f5; }}
                    </style>
                </head>
                <body>
                    <h1>Trading Report</h1>
                    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    {html}
                </body>
                </html>
                """
                with open(filepath, "w") as f:
                    f.write(html)
                self.logger.info(f"Report exported to HTML: {filepath}")

            else:
                self.logger.error(f"Unsupported export format: {format}")
                return None

            return filepath

        except Exception as e:
            self.logger.error(f"Error exporting report: {e}")
            return None

    def get_summary_metrics(self) -> Optional[Dict]:
        """
        Get overall summary metrics from all backtests.

        Returns:
            Dict with:
            - total_backtests: Count of all backtests
            - avg_sharpe_ratio: Average across all
            - avg_win_rate: Average win rate
            - best_strategy: Name of best performer
            - symbols_tested: Count of unique symbols
        """
        try:
            cursor = self.db.conn.cursor()

            # Overall statistics
            query = """
                SELECT 
                    COUNT(*) as total_backtests,
                    AVG(sharpe_ratio) as avg_sharpe,
                    AVG(win_rate) as avg_win_rate,
                    MAX(sharpe_ratio) as max_sharpe,
                    COUNT(DISTINCT symbol) as unique_symbols
                FROM backtest_backtests
            """

            cursor.execute(query)
            stats = cursor.fetchone()

            # Best strategy
            query_best = """
                SELECT 
                    bs.name,
                    AVG(bb.sharpe_ratio) as avg_sharpe
                FROM backtest_backtests bb
                JOIN backtest_strategies bs ON bb.strategy_id = bs.id
                GROUP BY bs.name
                ORDER BY avg_sharpe DESC
                LIMIT 1
            """

            cursor.execute(query_best)
            best = cursor.fetchone()

            return {
                "total_backtests": stats[0] if stats else 0,
                "avg_sharpe_ratio": round(stats[1], 4) if stats and stats[1] else 0,
                "avg_win_rate": round(stats[2], 4) if stats and stats[2] else 0,
                "max_sharpe_ratio": round(stats[3], 4) if stats and stats[3] else 0,
                "symbols_tested": stats[4] if stats else 0,
                "best_strategy": best[0] if best else "N/A",
                "best_strategy_sharpe": round(best[1], 4) if best and best[1] else 0,
            }

        except Exception as e:
            self.logger.error(f"Error calculating summary metrics: {e}")
            return None
