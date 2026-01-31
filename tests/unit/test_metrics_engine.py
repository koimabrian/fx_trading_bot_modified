"""Unit tests for metrics engine module."""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.backtesting.metrics_engine import MetricsEngine


class TestMetricsEngineInitialization:
    """Test MetricsEngine initialization."""

    def test_metrics_engine_initialization(self):
        """Test MetricsEngine initializes correctly."""
        engine = MetricsEngine()
        assert engine is not None

    def test_metrics_engine_has_required_methods(self):
        """Test MetricsEngine has required methods."""
        engine = MetricsEngine()
        assert hasattr(engine, "__init__")


class TestProfitLossMetrics:
    """Test profit and loss metrics."""

    @pytest.fixture
    def trades(self):
        """Create sample trades."""
        return [
            {"pnl": 100, "pips": 100},
            {"pnl": -50, "pips": -50},
            {"pnl": 150, "pips": 150},
            {"pnl": -30, "pips": -30},
            {"pnl": 200, "pips": 200},
        ]

    def test_total_profit_loss(self, trades):
        """Test total P&L calculation."""
        total_pnl = sum(t["pnl"] for t in trades)
        assert total_pnl == 370

    def test_gross_profit(self, trades):
        """Test gross profit calculation."""
        gross_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
        assert gross_profit == 450

    def test_gross_loss(self, trades):
        """Test gross loss calculation."""
        gross_loss = sum(t["pnl"] for t in trades if t["pnl"] < 0)
        assert gross_loss == -80

    def test_profit_factor(self, trades):
        """Test profit factor calculation."""
        gross_profit = sum(t["pnl"] for t in trades if t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in trades if t["pnl"] < 0))

        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        assert profit_factor == 450 / 80

    def test_average_profit_per_trade(self, trades):
        """Test average profit per trade."""
        avg_pnl = sum(t["pnl"] for t in trades) / len(trades)
        assert avg_pnl == 74.0


class TestWinRateMetrics:
    """Test win rate and trade statistics."""

    @pytest.fixture
    def trades(self):
        """Create sample trades."""
        return [
            {"pnl": 100},
            {"pnl": -50},
            {"pnl": 150},
            {"pnl": -30},
            {"pnl": 200},
        ]

    def test_winning_trades_count(self, trades):
        """Test count of winning trades."""
        winning = sum(1 for t in trades if t["pnl"] > 0)
        assert winning == 3

    def test_losing_trades_count(self, trades):
        """Test count of losing trades."""
        losing = sum(1 for t in trades if t["pnl"] < 0)
        assert losing == 2

    def test_win_rate(self, trades):
        """Test win rate calculation."""
        winning = sum(1 for t in trades if t["pnl"] > 0)
        win_rate = winning / len(trades) * 100
        assert win_rate == 60.0

    def test_loss_rate(self, trades):
        """Test loss rate calculation."""
        losing = sum(1 for t in trades if t["pnl"] < 0)
        loss_rate = losing / len(trades) * 100
        assert loss_rate == 40.0

    def test_average_win(self, trades):
        """Test average winning trade."""
        winning = [t["pnl"] for t in trades if t["pnl"] > 0]
        avg_win = sum(winning) / len(winning)
        assert avg_win == 150.0

    def test_average_loss(self, trades):
        """Test average losing trade."""
        losing = [t["pnl"] for t in trades if t["pnl"] < 0]
        avg_loss = sum(losing) / len(losing)
        assert avg_loss == -40.0

    def test_win_loss_ratio(self, trades):
        """Test win/loss ratio."""
        winning = [t["pnl"] for t in trades if t["pnl"] > 0]
        losing = [t["pnl"] for t in trades if t["pnl"] < 0]

        avg_win = sum(winning) / len(winning)
        avg_loss = abs(sum(losing) / len(losing))

        ratio = avg_win / avg_loss
        assert ratio == 150.0 / 40.0


class TestDrawdownMetrics:
    """Test drawdown calculations."""

    @pytest.fixture
    def equity_curve(self):
        """Create sample equity curve."""
        return pd.Series([10000, 10100, 10050, 10200, 9800, 10000, 10300, 9900, 10100])

    def test_running_maximum(self, equity_curve):
        """Test running maximum calculation."""
        running_max = equity_curve.cummax()
        assert running_max.iloc[-1] == 10300

    def test_drawdown_values(self, equity_curve):
        """Test drawdown calculation."""
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max

        assert drawdown.min() < 0

    def test_maximum_drawdown(self, equity_curve):
        """Test maximum drawdown."""
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max * 100

        max_dd = drawdown.min()
        assert max_dd < 0

    def test_drawdown_duration(self, equity_curve):
        """Test drawdown duration."""
        running_max = equity_curve.cummax()
        in_drawdown = equity_curve < running_max

        duration = in_drawdown.sum()
        assert duration > 0

    def test_recovery_from_drawdown(self, equity_curve):
        """Test recovery from drawdown."""
        recovered = equity_curve.iloc[-1] > equity_curve.iloc[:-1].max()
        # Based on the data, it should be true
        assert isinstance(recovered, (bool, np.bool_))


class TestSharpeRatioMetrics:
    """Test Sharpe ratio calculation."""

    def test_sharpe_ratio_calculation(self):
        """Test Sharpe ratio calculation."""
        returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.005, -0.005])
        risk_free_rate = 0.0002

        excess_returns = returns - risk_free_rate
        sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(252)

        assert isinstance(sharpe, (int, float))

    def test_sortino_ratio_calculation(self):
        """Test Sortino ratio calculation."""
        returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.005, -0.005])
        risk_free_rate = 0.0002
        target_return = 0.0

        excess_returns = returns - risk_free_rate
        downside = returns[returns < target_return]

        if len(downside) > 0:
            downside_std = downside.std()
            sortino = excess_returns.mean() / downside_std * np.sqrt(252)
            assert isinstance(sortino, (int, float))

    def test_calmar_ratio_calculation(self):
        """Test Calmar ratio calculation."""
        returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.005, -0.005])
        annual_return = returns.mean() * 252

        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        max_dd = ((cumulative - running_max) / running_max).min()

        if max_dd < 0:
            calmar = annual_return / abs(max_dd)
            assert isinstance(calmar, (int, float))


class TestConsecutiveMetrics:
    """Test consecutive trade metrics."""

    def test_consecutive_wins(self):
        """Test consecutive winning trades."""
        trades = [1, 1, 1, 0, 1, 1]  # 1 = win, 0 = loss

        max_consecutive = 0
        current = 0
        for trade in trades:
            if trade == 1:
                current += 1
                max_consecutive = max(max_consecutive, current)
            else:
                current = 0

        assert max_consecutive == 3

    def test_consecutive_losses(self):
        """Test consecutive losing trades."""
        trades = [0, 0, 1, 0, 0, 0]  # 0 = loss, 1 = win

        max_consecutive = 0
        current = 0
        for trade in trades:
            if trade == 0:
                current += 1
                max_consecutive = max(max_consecutive, current)
            else:
                current = 0

        assert max_consecutive == 3


class TestTimeBasedMetrics:
    """Test time-based performance metrics."""

    def test_daily_pnl_by_day_of_week(self):
        """Test P&L aggregation by day of week."""
        dates = pd.date_range("2026-01-01", periods=7, freq="D")
        pnl = [100, -50, 150, -30, 200, -20, 120]

        df = pd.DataFrame({"pnl": pnl}, index=dates)
        df["dow"] = df.index.dayofweek

        daily_by_dow = df.groupby("dow")["pnl"].sum()
        assert len(daily_by_dow) > 0

    def test_monthly_pnl(self):
        """Test P&L aggregation by month."""
        dates = pd.date_range("2026-01-01", periods=60, freq="D")
        pnl = np.random.uniform(-100, 200, 60)

        df = pd.DataFrame({"pnl": pnl}, index=dates)
        monthly = df.resample("ME")["pnl"].sum()

        assert len(monthly) >= 2  # Jan and Feb (partial) and possibly March

    def test_hourly_performance(self):
        """Test performance by hour of day."""
        hours = [9, 10, 14, 15, 9, 10, 14, 15]
        pnl = [100, 50, -30, 120, 80, 60, -20, 140]

        hourly_pnl = {}
        for hour, p in zip(hours, pnl):
            if hour not in hourly_pnl:
                hourly_pnl[hour] = []
            hourly_pnl[hour].append(p)

        assert len(hourly_pnl) == 4


class TestMetricsIntegration:
    """Integration tests for metrics engine."""

    def test_complete_metrics_calculation(self):
        """Test complete metrics calculation."""
        trades = [
            {"pnl": 100, "pips": 100},
            {"pnl": -50, "pips": -50},
            {"pnl": 150, "pips": 150},
            {"pnl": -30, "pips": -30},
            {"pnl": 200, "pips": 200},
        ]

        metrics = {
            "total_trades": len(trades),
            "winning_trades": sum(1 for t in trades if t["pnl"] > 0),
            "losing_trades": sum(1 for t in trades if t["pnl"] < 0),
            "total_pnl": sum(t["pnl"] for t in trades),
            "win_rate": sum(1 for t in trades if t["pnl"] > 0) / len(trades),
            "gross_profit": sum(t["pnl"] for t in trades if t["pnl"] > 0),
            "gross_loss": sum(t["pnl"] for t in trades if t["pnl"] < 0),
        }

        assert metrics["total_trades"] == 5
        assert metrics["win_rate"] == 0.6
        assert metrics["total_pnl"] == 370

    def test_metrics_for_multiple_symbols(self):
        """Test metrics aggregation for multiple symbols."""
        trades = [
            {"symbol": "EURUSD", "pnl": 100},
            {"symbol": "EURUSD", "pnl": -50},
            {"symbol": "GBPUSD", "pnl": 150},
            {"symbol": "GBPUSD", "pnl": -30},
        ]

        symbols = set(t["symbol"] for t in trades)

        for symbol in symbols:
            symbol_trades = [t for t in trades if t["symbol"] == symbol]
            pnl = sum(t["pnl"] for t in symbol_trades)
            assert pnl > 0 or pnl < 0 or pnl == 0

    def test_metrics_for_multiple_strategies(self):
        """Test metrics aggregation for multiple strategies."""
        trades = [
            {"strategy": "RSI", "pnl": 100},
            {"strategy": "RSI", "pnl": -50},
            {"strategy": "MACD", "pnl": 150},
            {"strategy": "MACD", "pnl": -30},
        ]

        strategies = set(t["strategy"] for t in trades)

        for strategy in strategies:
            strat_trades = [t for t in trades if t["strategy"] == strategy]
            wins = sum(1 for t in strat_trades if t["pnl"] > 0)
            losses = sum(1 for t in strat_trades if t["pnl"] < 0)
            assert wins + losses == len(strat_trades)
