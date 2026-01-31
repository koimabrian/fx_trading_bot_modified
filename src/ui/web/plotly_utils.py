"""Plotly chart utilities for consistent chart rendering across the dashboard."""

# Standard layout configuration for all bar charts
STANDARD_BAR_LAYOUT = {
    "margin": {"b": 80},
    "plot_bgcolor": "#f8fafc",
    "paper_bgcolor": "white",
}

# Standard layout configuration for heatmap
STANDARD_HEATMAP_LAYOUT = {
    "plot_bgcolor": "#f8fafc",
    "paper_bgcolor": "white",
}

# Standard Plotly config for responsive charts
RESPONSIVE_CONFIG = {"responsive": True}


def create_bar_chart(
    chart_id: str,
    x_data: list,
    y_data: list,
    title: str,
    x_label: str,
    y_label: str,
    colors: list = None,
):
    """Create and render a standard bar chart using Plotly.

    Handles color assignment based on values (green for positive, red for negative).

    Args:
        chart_id: HTML element ID where chart will be rendered
        x_data: X-axis data (labels)
        y_data: Y-axis data (values)
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        colors: Optional list of colors (defaults to green/red based on values)

    Example:
        >>> create_bar_chart(
        ...     'my-chart',
        ...     ['RSI', 'MACD', 'SMA'],
        ...     [1.2, 0.8, -0.5],
        ...     'Strategy Comparison',
        ...     'Strategy',
        ...     'Sharpe Ratio'
        ... )
    """
    if colors is None:
        colors = [
            "#10b981" if v >= 1 else "#f59e0b" if v >= 0 else "#ef4444" for v in y_data
        ]

    chart_data = [
        {
            "x": x_data,
            "y": y_data,
            "type": "bar",
            "marker": {"color": colors},
            "hovertemplate": "<b>%{x}</b><br>" + y_label + ": %{y:.3f}<extra></extra>",
        }
    ]

    layout = {
        "title": title,
        "xaxis": {"title": x_label},
        "yaxis": {"title": y_label},
        **STANDARD_BAR_LAYOUT,
    }

    # This would be called in JavaScript context
    return {
        "chart_id": chart_id,
        "data": chart_data,
        "layout": layout,
        "config": RESPONSIVE_CONFIG,
    }


def create_heatmap(
    chart_id: str,
    z_data: list,
    x_data: list,
    y_data: list,
    title: str,
    x_label: str = "Strategy",
    y_label: str = "Pair",
    colorscale: str = "RdYlGn",
):
    """Create and render a heatmap chart using Plotly.

    Args:
        chart_id: HTML element ID where chart will be rendered
        z_data: 2D matrix of values (list of lists)
        x_data: X-axis labels (strategies)
        y_data: Y-axis labels (pairs)
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        colorscale: Plotly colorscale name

    Example:
        >>> create_heatmap(
        ...     'my-heatmap',
        ...     [[1.5, 0.8, -0.2], [0.9, 1.2, 0.3]],
        ...     ['RSI', 'MACD', 'SMA'],
        ...     ['EURUSD', 'GBPUSD'],
        ...     'Performance Heatmap'
        ... )
    """
    chart_data = [
        {
            "z": z_data,
            "x": x_data,
            "y": y_data,
            "type": "heatmap",
            "colorscale": colorscale,
            "hovertemplate": "<b>%{y} × %{x}</b><br>Sharpe: %{z:.3f}<extra></extra>",
        }
    ]

    layout = {
        "title": title,
        "xaxis": {"title": x_label},
        "yaxis": {"title": y_label},
        **STANDARD_HEATMAP_LAYOUT,
    }

    return {
        "chart_id": chart_id,
        "data": chart_data,
        "layout": layout,
        "config": RESPONSIVE_CONFIG,
    }


def get_color_for_value(value: float, threshold_good: float = 1.0) -> str:
    """Get color code based on value (for conditional formatting).

    Args:
        value: Numeric value to evaluate
        threshold_good: Value above which color is green (default 1.0 for Sharpe ratio)

    Returns:
        Hex color code (#10b981 green, #f59e0b amber, #ef4444 red)
    """
    if value >= threshold_good:
        return "#10b981"  # Green
    elif value >= 0:
        return "#f59e0b"  # Amber
    else:
        return "#ef4444"  # Red


def get_colors_for_values(values: list, threshold_good: float = 1.0) -> list:
    """Get list of color codes for multiple values.

    Args:
        values: List of numeric values
        threshold_good: Value above which color is green

    Returns:
        List of hex color codes
    """
    return [get_color_for_value(v, threshold_good) for v in values]
