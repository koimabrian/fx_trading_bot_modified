"""
Report utilities and helpers.

Utility functions for report generation, data formatting, and transformations.
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import pandas as pd
import numpy as np


logger = logging.getLogger(__name__)


class ReportFormatter:
    """Format report data for display and export."""

    @staticmethod
    def format_percentage(value: float, decimals: int = 2) -> str:
        """Format number as percentage."""
        if value is None:
            return "N/A"
        return f"{value * 100:.{decimals}f}%"

    @staticmethod
    def format_currency(value: float, decimals: int = 2) -> str:
        """Format number as currency."""
        if value is None:
            return "N/A"
        return f"${value:,.{decimals}f}"

    @staticmethod
    def format_ratio(value: float, decimals: int = 3) -> str:
        """Format ratio (Sharpe, Sortino, etc.)."""
        if value is None:
            return "N/A"
        return f"{value:.{decimals}f}"

    @staticmethod
    def format_dataframe(
        df: pd.DataFrame, column_formats: Dict[str, str]
    ) -> pd.DataFrame:
        """
        Apply formatting to DataFrame columns.

        Args:
            df: DataFrame to format
            column_formats: Dict mapping column name to format type
                           ('percent', 'currency', 'ratio', 'float', 'int')

        Returns:
            Formatted DataFrame (copy)
        """
        df_formatted = df.copy()

        for column, format_type in column_formats.items():
            if column not in df_formatted.columns:
                continue

            if format_type == "percent":
                df_formatted[column] = df_formatted[column].apply(
                    lambda x: ReportFormatter.format_percentage(x)
                )
            elif format_type == "currency":
                df_formatted[column] = df_formatted[column].apply(
                    lambda x: ReportFormatter.format_currency(x)
                )
            elif format_type == "ratio":
                df_formatted[column] = df_formatted[column].apply(
                    lambda x: ReportFormatter.format_ratio(x)
                )
            elif format_type == "float":
                df_formatted[column] = df_formatted[column].apply(
                    lambda x: f"{x:.4f}" if x is not None else "N/A"
                )
            elif format_type == "int":
                df_formatted[column] = df_formatted[column].apply(
                    lambda x: f"{int(x)}" if x is not None else "N/A"
                )

        return df_formatted


class ReportAggregator:
    """Aggregate metrics across multiple reports."""

    @staticmethod
    def aggregate_sharpe_ratios(df: pd.DataFrame) -> Dict[str, float]:
        """
        Aggregate Sharpe ratios from report DataFrame.

        Args:
            df: DataFrame with sharpe_ratio column

        Returns:
            Dict with mean, median, min, max, std
        """
        if "sharpe_ratio" not in df.columns:
            return {}

        sharpe_values = df["sharpe_ratio"].dropna()

        return {
            "mean": float(sharpe_values.mean()),
            "median": float(sharpe_values.median()),
            "min": float(sharpe_values.min()),
            "max": float(sharpe_values.max()),
            "std": float(sharpe_values.std()),
        }

    @staticmethod
    def aggregate_win_rates(df: pd.DataFrame) -> Dict[str, float]:
        """Aggregate win rates."""
        if "win_rate" not in df.columns:
            return {}

        win_rates = df["win_rate"].dropna()

        return {
            "mean": float(win_rates.mean()),
            "median": float(win_rates.median()),
            "min": float(win_rates.min()),
            "max": float(win_rates.max()),
            "std": float(win_rates.std()),
        }

    @staticmethod
    def aggregate_returns(df: pd.DataFrame) -> Dict[str, float]:
        """Aggregate total returns."""
        if "total_return" not in df.columns:
            return {}

        returns = df["total_return"].dropna()

        return {
            "mean": float(returns.mean()),
            "median": float(returns.median()),
            "min": float(returns.min()),
            "max": float(returns.max()),
            "std": float(returns.std()),
            "sum": float(returns.sum()),
        }


class ReportValidator:
    """Validate report data integrity."""

    @staticmethod
    def validate_performance_report(df: pd.DataFrame) -> Tuple[bool, Optional[str]]:
        """
        Validate strategy performance report.

        Returns:
            (is_valid, error_message)
        """
        required_columns = [
            "symbol",
            "strategy",
            "timeframe",
            "sharpe_ratio",
            "total_return",
            "win_rate",
            "max_drawdown",
        ]

        # Check required columns
        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            return False, f"Missing columns: {missing}"

        # Check for nulls in critical fields
        critical_nulls = df[required_columns].isnull().sum()
        if critical_nulls.sum() > 0:
            return (
                False,
                f"Null values in critical fields: {critical_nulls[critical_nulls > 0].to_dict()}",
            )

        # Check numeric ranges
        if (df["sharpe_ratio"] < -100).any() or (df["sharpe_ratio"] > 100).any():
            return False, "Sharpe ratio out of expected range (-100, 100)"

        if (df["win_rate"] < 0).any() or (df["win_rate"] > 1).any():
            return False, "Win rate out of range (0, 1)"

        if (df["total_return"] < -1).any() or (df["total_return"] > 100).any():
            return False, "Total return out of expected range"

        return True, None

    @staticmethod
    def validate_volatility_ranking(df: pd.DataFrame) -> Tuple[bool, Optional[str]]:
        """Validate volatility ranking report."""
        required_columns = ["symbol", "atr_value", "volatility_level", "rank"]

        missing = [c for c in required_columns if c not in df.columns]
        if missing:
            return False, f"Missing columns: {missing}"

        # Check for duplicates
        if df["symbol"].duplicated().any():
            return False, "Duplicate symbols in ranking"

        # Check ATR values are positive
        if (df["atr_value"] <= 0).any():
            return False, "ATR values must be positive"

        # Check volatility levels are valid
        valid_levels = {"High", "Medium", "Low"}
        if not df["volatility_level"].isin(valid_levels).all():
            return False, f"Invalid volatility levels. Expected {valid_levels}"

        # Check ranking is sequential
        if list(df["rank"].values) != list(range(1, len(df) + 1)):
            return False, "Ranking is not sequential"

        return True, None


class ReportFilter:
    """Filter reports by various criteria."""

    @staticmethod
    def by_sharpe_threshold(df: pd.DataFrame, min_sharpe: float) -> pd.DataFrame:
        """Filter strategies by minimum Sharpe ratio."""
        if "sharpe_ratio" not in df.columns:
            return df
        return df[df["sharpe_ratio"] >= min_sharpe]

    @staticmethod
    def by_win_rate_threshold(df: pd.DataFrame, min_win_rate: float) -> pd.DataFrame:
        """Filter strategies by minimum win rate."""
        if "win_rate" not in df.columns:
            return df
        return df[df["win_rate"] >= min_win_rate]

    @staticmethod
    def by_trade_count(df: pd.DataFrame, min_trades: int) -> pd.DataFrame:
        """Filter strategies by minimum trade count."""
        if "trades_total" not in df.columns:
            return df
        return df[df["trades_total"] >= min_trades]

    @staticmethod
    def by_symbols(df: pd.DataFrame, symbols: List[str]) -> pd.DataFrame:
        """Filter to specific symbols."""
        if "symbol" not in df.columns:
            return df
        return df[df["symbol"].isin(symbols)]

    @staticmethod
    def by_volatility_level(df: pd.DataFrame, level: str) -> pd.DataFrame:
        """Filter volatility ranking by level (High, Medium, Low)."""
        if "volatility_level" not in df.columns:
            return df
        return df[df["volatility_level"] == level]

    @staticmethod
    def top_n_by_metric(df: pd.DataFrame, metric: str, n: int = 10) -> pd.DataFrame:
        """Get top N entries by metric."""
        if metric not in df.columns:
            return df
        return df.nlargest(n, metric)


class ReportComparison:
    """Compare reports across different periods/strategies."""

    @staticmethod
    def compare_strategies(reports: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Compare performance across multiple strategies.

        Args:
            reports: Dict mapping strategy name to report DataFrame

        Returns:
            Comparison DataFrame with aggregated metrics
        """
        comparison_data = []

        for strategy_name, df in reports.items():
            if df is None or len(df) == 0:
                continue

            sharpe_stats = ReportAggregator.aggregate_sharpe_ratios(df)
            win_rate_stats = ReportAggregator.aggregate_win_rates(df)
            return_stats = ReportAggregator.aggregate_returns(df)

            comparison_data.append(
                {
                    "strategy": strategy_name,
                    "symbols_tested": len(df),
                    "avg_sharpe": sharpe_stats.get("mean", 0),
                    "median_sharpe": sharpe_stats.get("median", 0),
                    "avg_win_rate": win_rate_stats.get("mean", 0),
                    "avg_return": return_stats.get("mean", 0),
                    "total_return": return_stats.get("sum", 0),
                }
            )

        return pd.DataFrame(comparison_data)

    @staticmethod
    def compare_periods(reports: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Compare performance across different time periods.

        Args:
            reports: Dict mapping period label to report DataFrame

        Returns:
            Comparison DataFrame
        """
        comparison_data = []

        for period_label, df in reports.items():
            if df is None or len(df) == 0:
                continue

            sharpe_stats = ReportAggregator.aggregate_sharpe_ratios(df)
            win_rate_stats = ReportAggregator.aggregate_win_rates(df)

            comparison_data.append(
                {
                    "period": period_label,
                    "trades_total": (
                        int(df["trades_total"].sum())
                        if "trades_total" in df.columns
                        else 0
                    ),
                    "avg_sharpe": sharpe_stats.get("mean", 0),
                    "avg_win_rate": win_rate_stats.get("mean", 0),
                }
            )

        return pd.DataFrame(comparison_data)
