# src/backtesting/metrics_engine.py
# Purpose: Calculate 15 comprehensive metrics for backtest results
import logging
from typing import Dict, List

import empyrical as ep
import pandas as pd

from src.utils.logging_factory import LoggingFactory


class MetricsEngine:
    """Calculate 15 comprehensive backtesting metrics.

    Provides methods to compute core metrics (Sharpe, drawdown, profit factor),
    trade statistics (win rate, P/L ratio), and bonus metrics (Sortino, Calmar).
    Uses empyrical library for accurate financial calculations.
    """

    def __init__(self):
        """Initialize metrics engine with logger."""
        self.logger = LoggingFactory.get_logger(__name__)

    def calculate_all_metrics(
        self,
        trades: List[Dict],
        returns: pd.Series,
    ) -> Dict[str, float]:
        """Calculate all 15 metrics from trades and returns.

        Args:
            trades: List of trade dicts with entry_time, exit_time, profit, profit_pct
            returns: Series of daily returns (index=date, values=returns)

        Returns:
            Dictionary with all 15 metrics
        """
        metrics = {}

        # Core metrics (5)
        metrics["total_profit_pct"] = self._total_profit_pct(trades)
        metrics["sharpe_ratio"] = self._sharpe_ratio(returns)
        metrics["annual_return_pct"] = self._annual_return_pct(returns)
        metrics["max_drawdown_pct"] = self._max_drawdown_pct(returns)
        metrics["profit_factor"] = self._profit_factor(trades)

        # Trade statistics (4)
        metrics["total_orders"] = len(trades)
        metrics["win_rate_pct"] = self._win_rate_pct(trades)
        metrics["pl_ratio"] = self._pl_ratio(trades)
        metrics["winner_avg_pct"] = self._winner_avg_pct(trades)
        metrics["loser_avg_pct"] = self._loser_avg_pct(trades)

        # Bonus metrics (3)
        metrics["sortino_ratio"] = self._sortino_ratio(returns)
        metrics["calmar_ratio"] = self._calmar_ratio(returns)
        metrics["recovery_factor"] = self._recovery_factor(trades, returns)

        self.logger.debug("Calculated 15 metrics")
        return metrics

    def calculate_rolling_metrics(
        self, returns: pd.Series, window_days: int = 180
    ) -> pd.DataFrame:
        """Calculate rolling profit metrics.

        Args:
            returns: Series of daily returns
            window_days: Window size in days

        Returns:
            DataFrame with rolling metrics
        """
        # Convert daily returns to cumulative returns
        cumulative = (1 + returns).cumprod() - 1

        rolling_data = []
        for i in range(len(returns)):
            if i < window_days:
                continue

            window_start = i - window_days
            window_return = cumulative.iloc[i] - cumulative.iloc[window_start]

            rolling_data.append(
                {
                    "date": returns.index[i],
                    "rolling_return_pct": window_return * 100,
                }
            )

        if not rolling_data:
            return pd.DataFrame()

        return pd.DataFrame(rolling_data).set_index("date")

    # ========== CORE METRICS (5) ==========

    def _total_profit_pct(self, trades: List[Dict]) -> float:
        """Calculate total profit as percentage of initial capital.

        Args:
            trades: List of trade dicts with profit key

        Returns:
            Profit percentage
        """
        if not trades:
            return 0.0

        total_profit = sum(t.get("profit", 0) for t in trades)
        return total_profit * 100

    def _sharpe_ratio(self, returns: pd.Series) -> float:
        """Calculate Sharpe ratio using empyrical.

        Args:
            returns: Series of daily returns

        Returns:
            Sharpe ratio (annualized)
        """
        if len(returns) < 2:
            return 0.0

        try:
            return float(ep.sharpe_ratio(returns, period="daily"))
        except (ValueError, ZeroDivisionError):
            return 0.0

    def _annual_return_pct(self, returns: pd.Series) -> float:
        """Calculate annualized return percentage.

        Args:
            returns: Series of daily returns

        Returns:
            Annual return percentage
        """
        if len(returns) < 2:
            return 0.0

        try:
            annual = ep.annual_return(returns, period="daily")
            return float(annual * 100)
        except (ValueError, ZeroDivisionError):
            return 0.0

    def _max_drawdown_pct(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown percentage.

        Args:
            returns: Series of daily returns

        Returns:
            Max drawdown as negative percentage (e.g., -15.5 for 15.5% loss)
        """
        if len(returns) < 2:
            return 0.0

        try:
            max_dd = ep.max_drawdown(returns)
            return float(max_dd * 100)
        except (ValueError, ZeroDivisionError):
            return 0.0

    def _profit_factor(self, trades: List[Dict]) -> float:
        """Calculate profit factor (Gross profit / Gross loss).

        Args:
            trades: List of trade dicts with profit_pct key

        Returns:
            Profit factor (>1 is good)
        """
        if not trades:
            return 0.0

        gross_profit = sum(
            t.get("profit_pct", 0) for t in trades if t.get("profit_pct", 0) > 0
        )
        gross_loss = abs(
            sum(t.get("profit_pct", 0) for t in trades if t.get("profit_pct", 0) < 0)
        )

        if gross_loss == 0:
            return gross_profit if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    # ========== TRADE STATISTICS (4) ==========

    def _win_rate_pct(self, trades: List[Dict]) -> float:
        """Calculate win rate percentage.

        Args:
            trades: List of trade dicts

        Returns:
            Win rate as percentage (0-100)
        """
        if not trades:
            return 0.0

        winning_trades = sum(1 for t in trades if t.get("profit_pct", 0) > 0)
        return (winning_trades / len(trades)) * 100

    def _pl_ratio(self, trades: List[Dict]) -> float:
        """Calculate profit/loss ratio (avg win / avg loss).

        Args:
            trades: List of trade dicts

        Returns:
            P/L ratio (>1 is good)
        """
        if not trades:
            return 0.0

        winning_trades = [t for t in trades if t.get("profit_pct", 0) > 0]
        losing_trades = [t for t in trades if t.get("profit_pct", 0) < 0]

        if not winning_trades or not losing_trades:
            return 0.0

        avg_win = sum(t.get("profit_pct", 0) for t in winning_trades) / len(
            winning_trades
        )
        avg_loss = abs(
            sum(t.get("profit_pct", 0) for t in losing_trades) / len(losing_trades)
        )

        if avg_loss == 0:
            return avg_win if avg_win > 0 else 0.0

        return avg_win / avg_loss

    def _winner_avg_pct(self, trades: List[Dict]) -> float:
        """Calculate average win percentage.

        Args:
            trades: List of trade dicts

        Returns:
            Average winning trade percentage
        """
        if not trades:
            return 0.0

        winning_trades = [t for t in trades if t.get("profit_pct", 0) > 0]

        if not winning_trades:
            return 0.0

        return sum(t.get("profit_pct", 0) for t in winning_trades) / len(winning_trades)

    def _loser_avg_pct(self, trades: List[Dict]) -> float:
        """Calculate average loss percentage.

        Args:
            trades: List of trade dicts

        Returns:
            Average losing trade percentage (as negative)
        """
        if not trades:
            return 0.0

        losing_trades = [t for t in trades if t.get("profit_pct", 0) < 0]

        if not losing_trades:
            return 0.0

        return sum(t.get("profit_pct", 0) for t in losing_trades) / len(losing_trades)

    # ========== BONUS METRICS (3) ==========

    def _sortino_ratio(self, returns: pd.Series) -> float:
        """Calculate Sortino ratio (return vs downside volatility).

        Args:
            returns: Series of daily returns

        Returns:
            Sortino ratio (annualized)
        """
        if len(returns) < 2:
            return 0.0

        try:
            return float(ep.sortino_ratio(returns, period="daily"))
        except (ValueError, ZeroDivisionError):
            return 0.0

    def _calmar_ratio(self, returns: pd.Series) -> float:
        """Calculate Calmar ratio (annual return / max drawdown).

        Args:
            returns: Series of daily returns

        Returns:
            Calmar ratio
        """
        if len(returns) < 2:
            return 0.0

        try:
            return float(ep.calmar_ratio(returns, period="daily"))
        except (ValueError, ZeroDivisionError):
            return 0.0

    def _recovery_factor(self, trades: List[Dict], returns: pd.Series) -> float:
        """Calculate recovery factor (net profit / max drawdown).

        Args:
            trades: List of trade dicts
            returns: Series of daily returns

        Returns:
            Recovery factor
        """
        net_profit = sum(t.get("profit", 0) for t in trades)
        max_dd = self._max_drawdown_pct(returns)

        if max_dd == 0 or net_profit == 0:
            return 0.0

        # Convert max_dd from percentage to decimal, keep as positive
        max_dd_abs = abs(max_dd / 100)

        return net_profit / max_dd_abs if max_dd_abs > 0 else 0.0

    # ========== UTILITIES ==========

    def format_metric(self, key: str, value: float) -> str:
        """Format metric value for display.

        Args:
            key: Metric name
            value: Metric value

        Returns:
            Formatted string
        """
        if key.endswith("_pct") or key.endswith("_ratio"):
            if key.endswith("_pct"):
                return f"{value:.2f}%"
            return f"{value:.2f}"
        return f"{value:.2f}"

    def get_metric_color(self, key: str, value: float) -> str:
        """Get display color for metric (green/red).

        Args:
            key: Metric name
            value: Metric value

        Returns:
            Color code ('green', 'red', 'yellow')
        """
        if key == "total_profit_pct":
            return "green" if value > 0 else "red"
        elif key == "sharpe_ratio":
            return "green" if value > 1 else ("yellow" if value > 0 else "red")
        elif key == "annual_return_pct":
            return "green" if value > 10 else ("yellow" if value > 0 else "red")
        elif key == "max_drawdown_pct":
            return "green" if value > -20 else ("yellow" if value > -30 else "red")
        elif key == "profit_factor":
            return "green" if value > 1.5 else ("yellow" if value > 1 else "red")
        elif key == "win_rate_pct":
            return "green" if value > 60 else ("yellow" if value > 50 else "red")
        else:
            return "yellow"
