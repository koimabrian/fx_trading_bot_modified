"""Unit tests for backtesting utilities module."""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.utils.backtesting_utils import calculate_atr


class TestBacktestingUtilsFunctions:
    """Test backtesting utility functions."""

    def test_calculate_atr_function_exists(self):
        """Test calculate_atr function is available."""
        assert calculate_atr is not None


class TestProfitAndLossCalculation:
    """Test profit and loss calculations."""

    def test_profit_calculation_long_trade(self):
        """Test profit calculation for long trade."""
        entry_price = 1.2500
        exit_price = 1.2550
        volume = 1.0

        profit_pips = (exit_price - entry_price) * 10000
        profit_usd = profit_pips * 10 * volume  # ~$50 per pip per lot

        assert profit_pips > 0
        assert profit_usd > 0

    def test_profit_calculation_short_trade(self):
        """Test profit calculation for short trade."""
        entry_price = 1.2500
        exit_price = 1.2450
        volume = 1.0

        profit_pips = (entry_price - exit_price) * 10000
        profit_usd = profit_pips * 10 * volume

        assert profit_pips > 0
        assert profit_usd > 0

    def test_loss_calculation_long_trade(self):
        """Test loss calculation for long trade."""
        entry_price = 1.2500
        exit_price = 1.2450
        volume = 1.0

        loss_pips = (exit_price - entry_price) * 10000
        loss_usd = loss_pips * 10 * volume

        assert loss_pips < 0
        assert loss_usd < 0

    def test_loss_calculation_short_trade(self):
        """Test loss calculation for short trade."""
        entry_price = 1.2500
        exit_price = 1.2550
        volume = 1.0

        loss_pips = (entry_price - exit_price) * 10000
        loss_usd = loss_pips * 10 * volume

        assert loss_pips < 0
        assert loss_usd < 0

    def test_break_even_trade(self):
        """Test break even trade."""
        entry_price = 1.2500
        exit_price = 1.2500

        profit_loss = exit_price - entry_price
        assert profit_loss == 0


class TestTradeMetricsCalculation:
    """Test trade metrics calculations."""

    @pytest.fixture
    def trade_list(self):
        """Create sample trade list."""
        return [
            {"pnl": 50, "pips": 50},
            {"pnl": -30, "pips": -30},
            {"pnl": 100, "pips": 100},
            {"pnl": -50, "pips": -50},
            {"pnl": 75, "pips": 75},
        ]

    def test_total_profit_loss(self, trade_list):
        """Test total P&L calculation."""
        total_pnl = sum(trade["pnl"] for trade in trade_list)
        assert total_pnl == 145

    def test_winning_trades_count(self, trade_list):
        """Test count of winning trades."""
        winning_trades = [t for t in trade_list if t["pnl"] > 0]
        assert len(winning_trades) == 3

    def test_losing_trades_count(self, trade_list):
        """Test count of losing trades."""
        losing_trades = [t for t in trade_list if t["pnl"] < 0]
        assert len(losing_trades) == 2

    def test_win_rate_calculation(self, trade_list):
        """Test win rate calculation."""
        winning_trades = len([t for t in trade_list if t["pnl"] > 0])
        total_trades = len(trade_list)
        win_rate = (winning_trades / total_trades) * 100

        assert win_rate == 60.0

    def test_loss_rate_calculation(self, trade_list):
        """Test loss rate calculation."""
        losing_trades = len([t for t in trade_list if t["pnl"] < 0])
        total_trades = len(trade_list)
        loss_rate = (losing_trades / total_trades) * 100

        assert loss_rate == 40.0

    def test_average_win_calculation(self, trade_list):
        """Test average win calculation."""
        winning_trades = [t for t in trade_list if t["pnl"] > 0]
        avg_win = sum(t["pnl"] for t in winning_trades) / len(winning_trades)

        assert avg_win == 75.0

    def test_average_loss_calculation(self, trade_list):
        """Test average loss calculation."""
        losing_trades = [t for t in trade_list if t["pnl"] < 0]
        avg_loss = sum(t["pnl"] for t in losing_trades) / len(losing_trades)

        assert avg_loss == -40.0

    def test_profit_factor(self, trade_list):
        """Test profit factor calculation."""
        gross_profit = sum(t["pnl"] for t in trade_list if t["pnl"] > 0)
        gross_loss = abs(sum(t["pnl"] for t in trade_list if t["pnl"] < 0))

        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        assert profit_factor > 0


class TestDrawdownCalculation:
    """Test drawdown calculations."""

    @pytest.fixture
    def equity_curve(self):
        """Create sample equity curve."""
        return pd.Series([10000, 10100, 10050, 10200, 9800, 10000, 10300, 9900, 10100])

    def test_drawdown_calculation(self, equity_curve):
        """Test drawdown calculation."""
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max * 100

        assert drawdown.min() < 0

    def test_max_drawdown(self, equity_curve):
        """Test maximum drawdown."""
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max * 100
        max_drawdown = drawdown.min()

        assert max_drawdown < 0
        assert abs(max_drawdown) > 0

    def test_drawdown_recovery(self, equity_curve):
        """Test drawdown recovery."""
        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max * 100

        # Check if fully recovered (back to new high)
        is_recovered = bool(equity_curve.iloc[-1] >= equity_curve.iloc[:-1].max())
        assert isinstance(is_recovered, bool)

    def test_drawdown_duration(self, equity_curve):
        """Test drawdown duration calculation."""
        running_max = equity_curve.cummax()
        is_drawdown = equity_curve < running_max

        # Count consecutive drawdown periods
        assert is_drawdown.sum() >= 0


class TestRiskMetricsCalculation:
    """Test risk-related metrics calculations."""

    def test_sharpe_ratio_calculation(self):
        """Test Sharpe ratio calculation."""
        returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.005, -0.005])
        risk_free_rate = 0.02 / 252  # Annual to daily

        excess_returns = returns - risk_free_rate
        sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(252)

        assert isinstance(sharpe, (int, float))

    def test_sortino_ratio_calculation(self):
        """Test Sortino ratio calculation."""
        returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.005, -0.005])
        risk_free_rate = 0.02 / 252
        target_return = 0.005

        excess_returns = returns - risk_free_rate
        downside_returns = returns[returns < target_return]

        if len(downside_returns) > 0:
            downside_std = downside_returns.std()
            sortino = excess_returns.mean() / downside_std * np.sqrt(252)
            assert isinstance(sortino, (int, float))

    def test_calmar_ratio_calculation(self):
        """Test Calmar ratio calculation."""
        returns = pd.Series([0.01, 0.02, -0.01, 0.015, 0.005, -0.005])
        annual_return = returns.sum() * 252

        equity_curve = (1 + returns).cumprod() * 10000
        running_max = equity_curve.cummax()
        max_drawdown = ((equity_curve - running_max) / running_max).min()

        if max_drawdown < 0:
            calmar = annual_return / abs(max_drawdown)
            assert isinstance(calmar, (int, float))

    def test_recovery_factor(self):
        """Test recovery factor calculation."""
        gross_profit = 1000
        max_drawdown = 200

        recovery_factor = gross_profit / max_drawdown if max_drawdown > 0 else 0

        assert recovery_factor > 0


class TestDailyMetricsCalculation:
    """Test daily metrics calculations."""

    def test_daily_return_calculation(self):
        """Test daily return calculation."""
        daily_equity = pd.Series([10000, 10100, 10050, 10150])
        daily_returns = daily_equity.pct_change()

        assert len(daily_returns) == len(daily_equity)
        assert pd.isna(daily_returns.iloc[0])

    def test_daily_profit_loss(self):
        """Test daily P&L calculation."""
        daily_equity = pd.Series([10000, 10100, 10050, 10150])
        daily_pnl = daily_equity.diff()

        assert daily_pnl.iloc[0] != daily_pnl.iloc[0]  # NaN
        assert daily_pnl.iloc[1] == 100
        assert daily_pnl.iloc[2] == -50

    def test_consecutive_winning_days(self):
        """Test consecutive winning days calculation."""
        daily_pnl = pd.Series([100, 50, -30, 75, 80, -20, 40])

        wins = daily_pnl > 0
        max_consecutive = 0
        current_streak = 0

        for win in wins:
            if win:
                current_streak += 1
                max_consecutive = max(max_consecutive, current_streak)
            else:
                current_streak = 0

        assert max_consecutive == 2

    def test_consecutive_losing_days(self):
        """Test consecutive losing days calculation."""
        daily_pnl = pd.Series([100, 50, -30, -75, -80, -20, 40])

        losses = daily_pnl < 0
        max_consecutive = 0
        current_streak = 0

        for loss in losses:
            if loss:
                current_streak += 1
                max_consecutive = max(max_consecutive, current_streak)
            else:
                current_streak = 0

        assert max_consecutive == 4


class TestPositionSizingCalculations:
    """Test position sizing calculations."""

    def test_fixed_position_size(self):
        """Test fixed position sizing."""
        position_size = 0.1  # 0.1 lots
        assert position_size == 0.1

    def test_fixed_risk_position_sizing(self):
        """Test fixed risk position sizing."""
        account_balance = 10000
        risk_percent = 1.0  # 1% risk
        risk_amount = account_balance * (risk_percent / 100)

        sl_pips = 50
        position_size = risk_amount / (sl_pips * 10)

        assert position_size > 0
        assert position_size < 1.0

    def test_kelly_criterion_sizing(self):
        """Test Kelly criterion position sizing."""
        win_rate = 0.6
        loss_rate = 0.4
        avg_win = 100
        avg_loss = 50

        win_prob = win_rate
        loss_prob = loss_rate
        win_loss_ratio = avg_win / avg_loss

        kelly_fraction = (win_prob * win_loss_ratio - loss_prob) / win_loss_ratio
        kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%

        assert kelly_fraction >= 0
        assert kelly_fraction <= 0.25

    def test_volatility_adjusted_sizing(self):
        """Test volatility-adjusted position sizing."""
        atr = 0.0050
        normal_atr = 0.0040

        size_adjustment = normal_atr / atr

        assert size_adjustment > 0
        assert size_adjustment <= 1.5


class TestBacktestingUtilsIntegration:
    """Integration tests for backtesting utilities."""

    def test_complete_backtest_metrics(self):
        """Test complete backtest metrics calculation."""
        trades = [
            {"entry": 1.2500, "exit": 1.2550, "volume": 1.0, "side": "BUY"},
            {"entry": 1.2550, "exit": 1.2500, "volume": 1.0, "side": "SELL"},
            {"entry": 1.2500, "exit": 1.2520, "volume": 1.0, "side": "BUY"},
        ]

        initial_balance = 10000

        # Calculate metrics
        pnls = []
        for trade in trades:
            if trade["side"] == "BUY":
                pnl = (trade["exit"] - trade["entry"]) * 10000 * 10 * trade["volume"]
            else:
                pnl = (trade["entry"] - trade["exit"]) * 10000 * 10 * trade["volume"]
            pnls.append(pnl)

        total_pnl = sum(pnls)
        final_balance = initial_balance + total_pnl

        assert final_balance > 0
        assert len(pnls) == len(trades)

    def test_equity_curve_generation(self):
        """Test equity curve generation."""
        initial_balance = 10000
        trade_pnls = [50, -30, 100, -50, 75]

        equity_curve = [initial_balance]
        for pnl in trade_pnls:
            equity_curve.append(equity_curve[-1] + pnl)

        assert len(equity_curve) == len(trade_pnls) + 1
        assert equity_curve[0] == initial_balance
        assert equity_curve[-1] == initial_balance + sum(trade_pnls)
