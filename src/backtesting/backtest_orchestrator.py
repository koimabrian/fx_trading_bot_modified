# src/backtesting/backtest_orchestrator.py
# Purpose: Orchestrates backtesting with metrics and trade logging
import logging
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from src.backtesting.metrics_engine import MetricsEngine
from src.backtesting.trade_logger import TradeLogger
from src.utils.logging_factory import LoggingFactory


class BacktestOrchestrator:
    """Orchestrates backtesting with integrated metrics and trade logging."""

    def __init__(self, symbol: str, strategy_name: str, timeframe: str):
        """Initialize backtest orchestrator.

        Args:
            symbol: Trading symbol
            strategy_name: Name of strategy being tested
            timeframe: Timeframe (e.g., 'M15', 'H1')
        """
        self.symbol = symbol
        self.strategy_name = strategy_name
        self.timeframe = timeframe

        self.logger = LoggingFactory.get_logger(__name__)
        self.metrics_engine = MetricsEngine()
        self.trade_logger = TradeLogger()

        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self.returns: Optional[pd.Series] = None

        self.logger.debug(
            "Initialized BacktestOrchestrator for %s (%s, %s)",
            symbol,
            strategy_name,
            timeframe,
        )

    def set_backtest_period(self, start_time: datetime, end_time: datetime) -> None:
        """Set the backtest time period.

        Args:
            start_time: Backtest start datetime
            end_time: Backtest end datetime
        """
        self.start_time = start_time
        self.end_time = end_time
        self.logger.debug("Backtest period set: %s to %s", start_time, end_time)

    def log_trade(
        self,
        entry_time: datetime,
        exit_time: datetime,
        entry_price: float,
        exit_price: float,
        volume: float,
        profit: float,
    ) -> None:
        """Log a completed trade.

        Args:
            entry_time: Entry datetime
            exit_time: Exit datetime
            entry_price: Entry price
            exit_price: Exit price
            volume: Trade volume
            profit: Profit amount
        """
        self.trade_logger.log_trade(
            entry_time=entry_time,
            exit_time=exit_time,
            symbol=self.symbol,
            entry_price=entry_price,
            exit_price=exit_price,
            volume=volume,
            profit=profit,
        )

    def set_returns(self, returns: pd.Series) -> None:
        """Set daily returns series for metrics calculation.

        Args:
            returns: pandas Series of daily returns (index=date, values=returns)
        """
        self.returns = returns
        self.logger.debug("Returns series set: %d periods", len(returns))

    def calculate_metrics(self) -> Dict[str, float]:
        """Calculate all 15 metrics from trades and returns.

        Returns:
            Dictionary with all metrics
        """
        if self.returns is None:
            self.logger.warning("Returns not set, cannot calculate metrics")
            return {}

        trades = self.trade_logger.get_trades()
        metrics = self.metrics_engine.calculate_all_metrics(trades, self.returns)

        self.logger.info(
            "Calculated %d metrics for %s",
            len(metrics),
            self.symbol,
        )
        return metrics

    def get_results_dict(self) -> Dict:
        """Get complete backtest results as dictionary.

        Returns:
            Dictionary with all backtest metadata and metrics
        """
        metrics = self.calculate_metrics()
        trades = self.trade_logger.get_trades()

        results = {
            "symbol": self.symbol,
            "strategy_name": self.strategy_name,
            "timeframe": self.timeframe,
            "start_date": self.start_time.isoformat() if self.start_time else None,
            "end_date": self.end_time.isoformat() if self.end_time else None,
            "created_at": datetime.now().isoformat(),
            "metrics": metrics,
            "trades": trades,
            "trade_count": len(trades),
        }

        return results

    def get_trades(self) -> List[Dict]:
        """Get all logged trades.

        Returns:
            List of trade dictionaries
        """
        return self.trade_logger.get_trades()

    def get_trades_df(self) -> pd.DataFrame:
        """Get all trades as pandas DataFrame.

        Returns:
            DataFrame with all trades
        """
        return self.trade_logger.get_trades_df()

    def get_summary(self) -> Dict:
        """Get summary statistics.

        Returns:
            Dictionary with summary statistics
        """
        return self.trade_logger.get_summary()

    def export_results(self, filepath: str) -> bool:
        """Export trades to CSV file.

        Args:
            filepath: Path to export CSV file

        Returns:
            True if successful, False otherwise
        """
        return self.trade_logger.export_to_csv(filepath)

    def print_summary(self) -> None:
        """Print backtest summary to logger.

        Logs all metrics, trade counts, and win rates in a formatted table.

        Returns:
            None.
        """
        metrics = self.calculate_metrics()
        summary = self.trade_logger.get_summary()

        self.logger.info("=" * 80)
        self.logger.info(
            "BACKTEST SUMMARY: %s (%s, %s)",
            self.symbol,
            self.strategy_name,
            self.timeframe,
        )
        self.logger.info("=" * 80)
        self.logger.info("Period: %s to %s", self.start_time, self.end_time)
        self.logger.info("-" * 80)
        self.logger.info("TRADES")
        self.logger.info("  Total Trades: %d", summary["total_trades"])
        self.logger.info("  Winning Trades: %d", summary["winning_trades"])
        self.logger.info("  Losing Trades: %d", summary["losing_trades"])
        self.logger.info("  Win Rate: %.2f%%", summary["win_rate"])
        self.logger.info("-" * 80)
        self.logger.info("METRICS")
        for metric_name in sorted(metrics.keys()):
            metric_value = metrics[metric_name]
            formatted = self.metrics_engine.format_metric(metric_name, metric_value)
            self.logger.info("  %s: %s", metric_name, formatted)
        self.logger.info("=" * 80)
