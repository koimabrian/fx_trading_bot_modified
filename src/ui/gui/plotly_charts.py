# src/ui/gui/plotly_charts.py
# Purpose: Generate interactive Plotly charts for backtesting results
import logging
from typing import Dict, List

import pandas as pd
import plotly.graph_objects as go

from src.utils.logging_factory import LoggingFactory


class PlotlyCharts:
    """Generate interactive Plotly charts for backtest visualization."""

    def __init__(self):
        """Initialize Plotly charts generator."""
        self.logger = LoggingFactory.get_logger(__name__)

    def create_equity_curve(
        self,
        trades: List[Dict],
        title: str = "Equity Curve",
        height: int = 500,
    ) -> go.Figure:
        """Create equity curve chart.

        Args:
            trades: List of trade dictionaries
            title: Chart title
            height: Chart height in pixels

        Returns:
            Plotly Figure object
        """
        if not trades:
            return self._empty_chart(title)

        # Calculate cumulative profit
        df = pd.DataFrame(trades)
        df["cumulative_profit"] = df["profit"].cumsum()
        df["exit_time"] = pd.to_datetime(df["exit_time"])
        df = df.sort_values("exit_time")

        # Create figure
        fig = go.Figure()

        # Add equity line
        fig.add_trace(
            go.Scatter(
                x=df["exit_time"],
                y=df["cumulative_profit"],
                mode="lines",
                name="Equity",
                line=dict(color="blue", width=2),
                fill="tozeroy",
                fillcolor="rgba(0, 0, 255, 0.1)",
                hovertemplate="<b>%{x|%Y-%m-%d %H:%M}</b><br>Equity: $%{y:.2f}<extra></extra>",
            )
        )

        # Add win/loss scatter
        wins = df[df["profit"] > 0]
        losses = df[df["profit"] < 0]

        if not wins.empty:
            fig.add_trace(
                go.Scatter(
                    x=wins["exit_time"],
                    y=wins["cumulative_profit"],
                    mode="markers",
                    name="Win",
                    marker=dict(color="green", size=8),
                    hovertemplate="<b>%{x|%Y-%m-%d %H:%M}</b><br>Profit: $%{y:.2f}<extra></extra>",
                )
            )

        if not losses.empty:
            fig.add_trace(
                go.Scatter(
                    x=losses["exit_time"],
                    y=losses["cumulative_profit"],
                    mode="markers",
                    name="Loss",
                    marker=dict(color="red", size=8),
                    hovertemplate="<b>%{x|%Y-%m-%d %H:%M}</b><br>Profit: $%{y:.2f}<extra></extra>",
                )
            )

        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Cumulative Profit ($)",
            hovermode="x unified",
            height=height,
            template="plotly_white",
            showlegend=True,
        )

        return fig

    def create_drawdown_chart(
        self,
        trades: List[Dict],
        title: str = "Drawdown",
        height: int = 400,
    ) -> go.Figure:
        """Create drawdown chart.

        Args:
            trades: List of trade dictionaries
            title: Chart title
            height: Chart height in pixels

        Returns:
            Plotly Figure object
        """
        if not trades:
            return self._empty_chart(title)

        df = pd.DataFrame(trades)
        df["cumulative_profit"] = df["profit"].cumsum()
        df["running_max"] = df["cumulative_profit"].cummax()
        df["drawdown"] = df["cumulative_profit"] - df["running_max"]
        df["exit_time"] = pd.to_datetime(df["exit_time"])
        df = df.sort_values("exit_time")

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=df["exit_time"],
                y=df["drawdown"],
                mode="lines",
                name="Drawdown",
                line=dict(color="red", width=2),
                fill="tozeroy",
                fillcolor="rgba(255, 0, 0, 0.2)",
                hovertemplate="<b>%{x|%Y-%m-%d %H:%M}</b><br>Drawdown: $%{y:.2f}<extra></extra>",
            )
        )

        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Drawdown ($)",
            hovermode="x unified",
            height=height,
            template="plotly_white",
        )

        return fig

    def create_trade_distribution(
        self,
        trades: List[Dict],
        title: str = "Trade P&L Distribution",
        height: int = 400,
    ) -> go.Figure:
        """Create trade P&L distribution histogram.

        Args:
            trades: List of trade dictionaries
            title: Chart title
            height: Chart height in pixels

        Returns:
            Plotly Figure object
        """
        if not trades:
            return self._empty_chart(title)

        df = pd.DataFrame(trades)

        fig = go.Figure()

        fig.add_trace(
            go.Histogram(
                x=df["profit_pct"],
                name="Trade P&L %",
                marker_color="lightblue",
                nbinsx=20,
                hovertemplate="P&L Range: %{x:.2f}%<br>Count: %{y}<extra></extra>",
            )
        )

        # Add zero line
        fig.add_vline(
            x=0, line_dash="dash", line_color="red", annotation_text="Break-even"
        )

        fig.update_layout(
            title=title,
            xaxis_title="Trade P&L (%)",
            yaxis_title="Frequency",
            hovermode="x unified",
            height=height,
            template="plotly_white",
        )

        return fig

    def create_metrics_comparison(
        self,
        metrics: Dict[str, float],
        title: str = "Key Metrics",
        height: int = 400,
    ) -> go.Figure:
        """Create metrics comparison bar chart.

        Args:
            metrics: Dictionary of metric names and values
            title: Chart title
            height: Chart height in pixels

        Returns:
            Plotly Figure object
        """
        if not metrics:
            return self._empty_chart(title)

        # Select key metrics for display
        key_metrics = [
            "sharpe_ratio",
            "annual_return_pct",
            "max_drawdown_pct",
            "profit_factor",
            "win_rate_pct",
        ]

        plot_data = {k: metrics.get(k, 0) for k in key_metrics if k in metrics}

        fig = go.Figure()

        colors = ["green" if v > 0 else "red" for v in plot_data.values()]

        fig.add_trace(
            go.Bar(
                x=list(plot_data.keys()),
                y=list(plot_data.values()),
                marker_color=colors,
                hovertemplate="<b>%{x}</b><br>Value: %{y:.2f}<extra></extra>",
            )
        )

        fig.update_layout(
            title=title,
            xaxis_title="Metric",
            yaxis_title="Value",
            height=height,
            template="plotly_white",
            showlegend=False,
        )

        return fig

    def create_monthly_returns(
        self,
        trades: List[Dict],
        title: str = "Monthly Returns",
        height: int = 400,
    ) -> go.Figure:
        """Create monthly returns heatmap.

        Args:
            trades: List of trade dictionaries
            title: Chart title
            height: Chart height in pixels

        Returns:
            Plotly Figure object
        """
        if not trades:
            return self._empty_chart(title)

        df = pd.DataFrame(trades)
        df["exit_time"] = pd.to_datetime(df["exit_time"])
        df["year_month"] = df["exit_time"].dt.to_period("M")

        monthly_returns = df.groupby("year_month")["profit_pct"].sum().reset_index()
        monthly_returns["year_month"] = monthly_returns["year_month"].astype(str)

        fig = go.Figure()

        colors = ["green" if v > 0 else "red" for v in monthly_returns["profit_pct"]]

        fig.add_trace(
            go.Bar(
                x=monthly_returns["year_month"],
                y=monthly_returns["profit_pct"],
                marker_color=colors,
                hovertemplate="<b>%{x}</b><br>Return: %{y:.2f}%<extra></extra>",
            )
        )

        fig.update_layout(
            title=title,
            xaxis_title="Month",
            yaxis_title="Return (%)",
            height=height,
            template="plotly_white",
            showlegend=False,
        )

        return fig

    def _empty_chart(self, title: str) -> go.Figure:
        """Create empty chart placeholder.

        Args:
            title: Chart title

        Returns:
            Plotly Figure object
        """
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        fig.update_layout(title=title, template="plotly_white")
        return fig
