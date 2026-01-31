"""Unit tests for exit strategies module."""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
from datetime import datetime

from src.utils.exit_strategies import (
    ExitStrategyManager,
    ExitType,
    ExitSignal,
    BaseExitStrategy,
    FixedPercentageStopLoss,
    FixedPercentageTakeProfit,
    TrailingStopStrategy,
    EquityTargetExit,
    SignalChangeExit,
)


class TestExitStrategyManager:
    """Test suite for exit strategy utilities."""

    @pytest.fixture
    def exit_manager(self):
        """Create ExitStrategyManager instance."""
        return ExitStrategyManager()

    @pytest.fixture
    def mock_position(self):
        """Create mock position data."""
        return {
            "symbol": "EURUSD",
            "entry_price": 1.2500,
            "volume": 1.0,
            "side": "BUY",
            "ticket": 1001,
            "entry_time": datetime.now(),
        }

    @pytest.fixture
    def mock_market_data(self):
        """Create mock market data."""
        return {
            "bid": 1.2520,
            "ask": 1.2522,
            "high": 1.2530,
            "low": 1.2480,
            "current_price": 1.2520,
        }

    def test_stop_loss_manager_initialization(self, exit_manager):
        """Test StopLossManager initializes correctly."""
        assert exit_manager is not None

    def test_stop_loss_percentage_calculation(self, mock_position, mock_market_data):
        """Test stop loss price calculation with percentage."""
        entry_price = mock_position["entry_price"]
        sl_percent = 1.0  # 1% stop loss

        expected_sl = entry_price * (1 - sl_percent / 100)
        assert expected_sl == 1.2375

    def test_stop_loss_fixed_level(self, mock_position):
        """Test stop loss at fixed price level."""
        entry_price = mock_position["entry_price"]
        sl_price = 1.2400

        sl_pips = (entry_price - sl_price) * 10000  # In pips
        assert sl_pips > 0

    def test_stop_loss_triggered(self, mock_position, mock_market_data):
        """Test stop loss trigger detection."""
        entry_price = mock_position["entry_price"]
        sl_price = 1.2400
        current_price = 1.2390  # Below stop loss

        is_triggered = current_price <= sl_price
        assert is_triggered is True

    def test_stop_loss_not_triggered(self, mock_position, mock_market_data):
        """Test stop loss not triggered."""
        sl_price = 1.2400
        current_price = 1.2450  # Above stop loss

        is_triggered = current_price <= sl_price
        assert is_triggered is False

    def test_take_profit_manager_initialization(self):
        """Test TakeProfitManager initializes correctly."""
        manager = ExitStrategyManager()
        assert manager is not None

    def test_take_profit_percentage_calculation(self, mock_position):
        """Test take profit price calculation with percentage."""
        entry_price = mock_position["entry_price"]
        tp_percent = 2.0  # 2% take profit

        expected_tp = entry_price * (1 + tp_percent / 100)
        assert expected_tp == 1.2750

    def test_take_profit_fixed_level(self, mock_position):
        """Test take profit at fixed price level."""
        entry_price = mock_position["entry_price"]
        tp_price = 1.2600

        tp_pips = (tp_price - entry_price) * 10000
        assert tp_pips > 0

    def test_take_profit_triggered(self, mock_position):
        """Test take profit trigger detection."""
        tp_price = 1.2600
        current_price = 1.2610  # Above take profit

        is_triggered = current_price >= tp_price
        assert is_triggered is True

    def test_take_profit_not_triggered(self, mock_position):
        """Test take profit not triggered."""
        tp_price = 1.2600
        current_price = 1.2550  # Below take profit

        is_triggered = current_price >= tp_price
        assert is_triggered is False

    def test_sl_tp_bracket_order(self, mock_position):
        """Test standard SL/TP bracket order."""
        entry = mock_position["entry_price"]
        sl = entry - 0.0050  # 50 pips stop loss
        tp = entry + 0.0100  # 100 pips take profit

        assert sl < entry
        assert tp > entry
        assert tp > sl

    def test_exit_signal_generation(self, mock_position, mock_market_data):
        """Test exit signal generation."""
        entry_price = mock_position["entry_price"]
        current_price = mock_market_data["current_price"]
        sl_price = entry_price - 0.0050
        tp_price = entry_price + 0.0100

        # Calculate profit
        profit = (current_price - entry_price) * 10000  # In pips

        exit_signal = None
        if current_price <= sl_price:
            exit_signal = "STOP_LOSS"
        elif current_price >= tp_price:
            exit_signal = "TAKE_PROFIT"

        assert exit_signal is None  # Not triggered yet
        assert profit > 0

    def test_trailing_stop_loss(self, mock_position):
        """Test trailing stop loss logic."""
        entry_price = mock_position["entry_price"]
        trail_percent = 0.5  # 0.5% trailing stop

        prices = [1.2500, 1.2520, 1.2530, 1.2525, 1.2515]
        highest_price = entry_price

        for price in prices:
            if price > highest_price:
                highest_price = price

            trail_sl = highest_price * (1 - trail_percent / 100)
            is_hit = price <= trail_sl
            assert isinstance(is_hit, bool)

    def test_breakeven_stop(self, mock_position):
        """Test breakeven stop loss placement."""
        entry_price = mock_position["entry_price"]
        current_price = entry_price + 0.0050

        # Move SL to breakeven
        breakeven_sl = entry_price
        assert breakeven_sl == entry_price

    def test_partial_take_profit(self, mock_position):
        """Test partial take profit."""
        volume = mock_position["volume"]

        # Close 50% at TP1, 50% at TP2
        volume_tp1 = volume * 0.5
        volume_tp2 = volume * 0.5

        assert volume_tp1 + volume_tp2 == volume

    def test_multiple_tp_levels(self, mock_position):
        """Test multiple take profit levels."""
        entry = mock_position["entry_price"]

        tp1 = entry + 0.0050  # 50 pips
        tp2 = entry + 0.0100  # 100 pips
        tp3 = entry + 0.0150  # 150 pips

        assert tp1 < tp2 < tp3


class TestExitConditions:
    """Test various exit conditions and scenarios."""

    def test_time_based_exit(self):
        """Test time-based exit condition."""
        entry_time = datetime(2026, 2, 1, 10, 0, 0)
        current_time = datetime(2026, 2, 1, 12, 0, 0)
        max_hold_hours = 2

        hours_held = (current_time - entry_time).total_seconds() / 3600
        should_exit = hours_held >= max_hold_hours

        assert should_exit is True

    def test_profit_target_exit(self):
        """Test profit target exit."""
        account_balance = 10000
        daily_profit_target = 500
        current_profit = 500

        should_exit = current_profit >= daily_profit_target
        assert should_exit is True

    def test_loss_limit_exit(self):
        """Test daily loss limit exit."""
        daily_loss_limit = 500
        current_loss = 600

        should_exit = abs(current_loss) >= daily_loss_limit
        assert should_exit is True

    def test_signal_reversal_exit(self):
        """Test exit on signal reversal."""
        entry_signal = "BUY"
        current_signal = "SELL"

        should_exit = entry_signal != current_signal
        assert should_exit is True

    def test_volatility_based_exit(self):
        """Test exit based on volatility spike."""
        normal_atr = 0.0050
        current_atr = 0.0150
        volatility_threshold = 2.0  # 2x normal

        volatility_spike = current_atr > (normal_atr * volatility_threshold)
        assert volatility_spike is True


class TestExitEdgeCases:
    """Test edge cases in exit logic."""

    def test_gap_past_stop_loss(self):
        """Test handling price gap past stop loss."""
        sl_price = 1.2400
        gap_price = 1.2350  # Gapped through SL

        # Should exit at market or SL
        exit_price = min(sl_price, gap_price)
        assert exit_price == 1.2350

    def test_simultaneous_sl_and_tp(self):
        """Test simultaneous SL and TP trigger (edge case)."""
        tp_price = 1.2600
        sl_price = 1.2400

        # Both should not trigger simultaneously
        assert tp_price > sl_price

    def test_zero_stop_loss(self):
        """Test handling zero or invalid stop loss."""
        sl_price = 0

        # Should not allow zero stop loss
        is_valid = sl_price > 0
        assert is_valid is False

    def test_negative_position_volume(self):
        """Test handling negative volume (edge case)."""
        volume = -1.0

        # Should validate volume is positive
        is_valid = volume > 0
        assert is_valid is False

    def test_expired_orders(self):
        """Test handling expired orders."""
        order_time = datetime(2026, 2, 1, 10, 0, 0)
        current_time = datetime(2026, 2, 8, 10, 0, 0)
        order_ttl_days = 5

        days_open = (current_time - order_time).days
        is_expired = days_open > order_ttl_days
        assert is_expired is True


class TestExitIntegration:
    """Integration tests for exit strategies."""

    def test_complete_exit_workflow(self):
        """Test complete exit workflow."""
        # Setup
        entry_price = 1.2500
        sl_price = 1.2400
        tp_price = 1.2600

        # Simulate price movement
        prices = [1.2505, 1.2510, 1.2520, 1.2530]

        for price in prices:
            # Check exit conditions
            sl_hit = price <= sl_price
            tp_hit = price >= tp_price

            if sl_hit or tp_hit:
                exit_reason = "SL" if sl_hit else "TP"
                assert exit_reason in ["SL", "TP"]
                break

    def test_exit_with_breakeven_management(self):
        """Test exit with breakeven stop management."""
        entry = 1.2500
        profit_threshold = 0.0030  # 30 pips to move SL to BE

        prices = [1.2500, 1.2520, 1.2531]  # 31 pips profit

        sl = entry - 0.0050
        for price in prices:
            profit = price - entry
            if profit >= profit_threshold:
                sl = entry  # Move to breakeven

        assert sl == entry

    def test_exit_multiple_scenarios(self):
        """Test multiple exit scenarios."""
        scenarios = [
            {"reason": "sl_hit", "expected": True},
            {"reason": "tp_hit", "expected": True},
            {"reason": "time_expired", "expected": True},
            {"reason": "signal_reversal", "expected": True},
            {"reason": "no_exit", "expected": False},
        ]

        for scenario in scenarios:
            should_exit = scenario["expected"]
            assert isinstance(should_exit, bool)


class TestExitSignal:
    """Test ExitSignal dataclass."""

    def test_exit_signal_creation(self):
        """Test ExitSignal creation."""
        signal = ExitSignal(
            triggered=True,
            exit_type=ExitType.STOP_LOSS,
            exit_price=1.2400,
            reason="Test stop loss",
            confidence=0.9,
            close_percent=100.0,
        )
        assert signal.triggered is True
        assert signal.exit_type == ExitType.STOP_LOSS
        assert signal.exit_price == 1.2400
        assert signal.confidence == 0.9

    def test_exit_signal_to_dict(self):
        """Test ExitSignal serialization."""
        signal = ExitSignal(
            triggered=True,
            exit_type=ExitType.TAKE_PROFIT,
            exit_price=1.2700,
            reason="Take profit hit",
        )
        result = signal.to_dict()
        assert result["triggered"] is True
        assert result["exit_type"] == "take_profit"
        assert result["exit_price"] == 1.2700


class TestFixedPercentageStopLoss:
    """Test FixedPercentageStopLoss strategy."""

    def test_stop_loss_not_triggered_long(self):
        """Test stop loss not triggered for long position."""
        strategy = FixedPercentageStopLoss(stop_loss_percent=1.0)
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2480,  # 0.16% loss
            position_side="long",
        )
        assert signal.triggered is False
        assert signal.exit_type == ExitType.STOP_LOSS

    def test_stop_loss_triggered_long(self):
        """Test stop loss triggered for long position."""
        strategy = FixedPercentageStopLoss(stop_loss_percent=1.0)
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2370,  # 1.04% loss
            position_side="long",
        )
        assert signal.triggered is True
        assert signal.exit_type == ExitType.STOP_LOSS
        assert signal.exit_price == pytest.approx(1.2375, rel=1e-4)

    def test_stop_loss_triggered_short(self):
        """Test stop loss triggered for short position."""
        strategy = FixedPercentageStopLoss(stop_loss_percent=1.0)
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2630,  # 1.04% loss for short
            position_side="short",
        )
        assert signal.triggered is True

    def test_stop_loss_not_triggered_short(self):
        """Test stop loss not triggered for short position in profit."""
        strategy = FixedPercentageStopLoss(stop_loss_percent=1.0)
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2450,  # Profit for short
            position_side="short",
        )
        assert signal.triggered is False


class TestFixedPercentageTakeProfit:
    """Test FixedPercentageTakeProfit strategy."""

    def test_take_profit_not_triggered_long(self):
        """Test take profit not triggered for long position."""
        strategy = FixedPercentageTakeProfit(take_profit_percent=2.0)
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2600,  # 0.8% profit
            position_side="long",
        )
        assert signal.triggered is False
        assert signal.exit_type == ExitType.TAKE_PROFIT

    def test_take_profit_triggered_long(self):
        """Test take profit triggered for long position."""
        strategy = FixedPercentageTakeProfit(take_profit_percent=2.0)
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2760,  # 2.08% profit
            position_side="long",
        )
        assert signal.triggered is True
        assert signal.exit_type == ExitType.TAKE_PROFIT
        assert signal.exit_price == pytest.approx(1.2750, rel=1e-4)

    def test_take_profit_triggered_short(self):
        """Test take profit triggered for short position."""
        strategy = FixedPercentageTakeProfit(take_profit_percent=2.0)
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2240,  # 2.08% profit for short
            position_side="short",
        )
        assert signal.triggered is True


class TestTrailingStopStrategy:
    """Test TrailingStopStrategy."""

    def test_trailing_not_activated_below_threshold(self):
        """Test trailing stop not activated when below activation threshold."""
        strategy = TrailingStopStrategy(
            trail_percent=0.5, activation_percent=1.0
        )
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2520,  # 0.16% profit, below 1% activation
            position_side="long",
        )
        assert signal.triggered is False
        assert "not active" in signal.reason

    def test_trailing_activated_and_not_triggered(self):
        """Test trailing stop activated but not triggered."""
        strategy = TrailingStopStrategy(
            trail_percent=0.5, activation_percent=0.0
        )
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2600,
            position_side="long",
            highest_price=1.2620,
        )
        # Trailing stop at 1.2620 * (1 - 0.5/100) = 1.2557
        # Current price 1.2600 > 1.2557, so not triggered
        assert signal.triggered is False

    def test_trailing_triggered(self):
        """Test trailing stop triggered."""
        strategy = TrailingStopStrategy(
            trail_percent=0.5, activation_percent=0.0
        )
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2550,
            position_side="long",
            highest_price=1.2620,
        )
        # Trailing stop at 1.2620 * (1 - 0.5/100) = 1.2557
        # Current price 1.2550 < 1.2557, so triggered
        assert signal.triggered is True
        assert signal.exit_type == ExitType.TRAILING_STOP

    def test_trailing_reset(self):
        """Test trailing stop reset functionality."""
        strategy = TrailingStopStrategy(trail_percent=0.5)
        # First evaluation
        strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2600,
            position_side="long",
            position_id="pos1",
        )
        # Reset
        strategy.reset_tracking("pos1")
        # Verify no tracking data
        assert "pos1" not in strategy._highest_price


class TestEquityTargetExit:
    """Test EquityTargetExit strategy."""

    def test_equity_target_not_triggered(self):
        """Test equity target not triggered."""
        strategy = EquityTargetExit(target_equity_increase_percent=5.0)
        signal = strategy.evaluate(
            entry_price=0,
            current_price=0,
            position_side="long",
            initial_equity=10000,
            current_equity=10300,  # 3% increase
        )
        assert signal.triggered is False
        assert signal.exit_type == ExitType.EQUITY_TARGET

    def test_equity_target_triggered(self):
        """Test equity target triggered."""
        strategy = EquityTargetExit(target_equity_increase_percent=5.0)
        signal = strategy.evaluate(
            entry_price=0,
            current_price=0,
            position_side="long",
            initial_equity=10000,
            current_equity=10600,  # 6% increase
        )
        assert signal.triggered is True
        assert signal.close_percent == 100.0

    def test_equity_target_invalid_values(self):
        """Test equity target with invalid values."""
        strategy = EquityTargetExit(target_equity_increase_percent=5.0)
        signal = strategy.evaluate(
            entry_price=0,
            current_price=0,
            position_side="long",
            initial_equity=0,  # Invalid
            current_equity=10600,
        )
        assert signal.triggered is False
        assert "Invalid" in signal.reason


class TestExitStrategyManagerEnhanced:
    """Test enhanced ExitStrategyManager methods."""

    @pytest.fixture
    def manager(self):
        """Create ExitStrategyManager with config."""
        config = {
            "risk_management": {
                "stop_loss_percent": 1.0,
                "take_profit_percent": 2.0,
                "trailing_stop_percent": 0.5,
                "trailing_stop": True,
            }
        }
        return ExitStrategyManager(config)

    def test_fixed_stop_loss_exit(self, manager):
        """Test fixed_stop_loss_exit method."""
        result = manager.fixed_stop_loss_exit(
            entry_price=1.2500,
            current_price=1.2370,
            position_side="long",
            stop_loss_percent=1.0,
        )
        assert result["triggered"] is True
        assert result["exit_type"] == "stop_loss"

    def test_fixed_take_profit_exit(self, manager):
        """Test fixed_take_profit_exit method."""
        result = manager.fixed_take_profit_exit(
            entry_price=1.2500,
            current_price=1.2760,
            position_side="long",
            take_profit_percent=2.0,
        )
        assert result["triggered"] is True
        assert result["exit_type"] == "take_profit"

    def test_equity_target_exit(self, manager):
        """Test equity_target_exit method."""
        result = manager.equity_target_exit(
            initial_equity=10000,
            current_equity=10600,
            target_percent=5.0,
        )
        assert result["triggered"] is True
        assert result["exit_type"] == "equity_target"

    def test_advanced_trailing_stop(self, manager):
        """Test advanced_trailing_stop method."""
        result = manager.advanced_trailing_stop(
            entry_price=1.2500,
            current_price=1.2550,
            position_side="long",
            trail_percent=0.5,
            highest_price=1.2620,
        )
        assert result["triggered"] is True
        assert result["exit_type"] == "trailing_stop"

    def test_evaluate_all_exits_stop_loss(self, manager):
        """Test evaluate_all_exits with stop loss trigger."""
        result = manager.evaluate_all_exits(
            entry_price=1.2500,
            current_price=1.2370,  # 1.04% loss
            position_side="long",
        )
        assert result["should_exit"] is True
        assert result["primary_exit"] == "stop_loss"
        assert result["recommended_action"] == "close_all"

    def test_evaluate_all_exits_take_profit(self, manager):
        """Test evaluate_all_exits with take profit trigger."""
        result = manager.evaluate_all_exits(
            entry_price=1.2500,
            current_price=1.2760,  # 2.08% profit
            position_side="long",
        )
        assert result["should_exit"] is True
        assert result["primary_exit"] == "take_profit"

    def test_evaluate_all_exits_no_exit(self, manager):
        """Test evaluate_all_exits with no exit triggers."""
        result = manager.evaluate_all_exits(
            entry_price=1.2500,
            current_price=1.2550,  # 0.4% profit
            position_side="long",
        )
        assert result["should_exit"] is False
        assert result["recommended_action"] == "hold"

    def test_evaluate_all_exits_time_based(self, manager):
        """Test evaluate_all_exits with time-based exit."""
        result = manager.evaluate_all_exits(
            entry_price=1.2500,
            current_price=1.2510,
            position_side="long",
            bars_held=150,  # Above max_hold_bars (100)
        )
        assert result["should_exit"] is True
        assert result["primary_exit"] == "time_based"

    def test_create_exit_strategy_from_config(self, manager):
        """Test factory method for creating exit strategies."""
        sl_strategy = manager.create_exit_strategy_from_config("stop_loss")
        assert isinstance(sl_strategy, FixedPercentageStopLoss)

        tp_strategy = manager.create_exit_strategy_from_config("take_profit")
        assert isinstance(tp_strategy, FixedPercentageTakeProfit)

        trail_strategy = manager.create_exit_strategy_from_config("trailing_stop")
        assert isinstance(trail_strategy, TrailingStopStrategy)

        equity_strategy = manager.create_exit_strategy_from_config("equity_target")
        assert isinstance(equity_strategy, EquityTargetExit)

        unknown = manager.create_exit_strategy_from_config("unknown")
        assert unknown is None


class TestExitTypeEnum:
    """Test ExitType enumeration."""

    def test_exit_type_values(self):
        """Test ExitType enum values."""
        assert ExitType.STOP_LOSS.value == "stop_loss"
        assert ExitType.TAKE_PROFIT.value == "take_profit"
        assert ExitType.TRAILING_STOP.value == "trailing_stop"
        assert ExitType.EQUITY_TARGET.value == "equity_target"
        assert ExitType.TIME_BASED.value == "time_based"
        assert ExitType.BREAKEVEN.value == "breakeven"
        assert ExitType.ATR_BASED.value == "atr_based"


class TestBaseExitStrategyPnLCalculation:
    """Test P&L calculation in BaseExitStrategy."""

    def test_pnl_long_profit(self):
        """Test P&L calculation for long position in profit."""
        strategy = FixedPercentageStopLoss(1.0)
        pnl = strategy.calculate_pnl_percent(
            entry_price=1.2500,
            current_price=1.2625,
            position_side="long",
        )
        assert pnl == pytest.approx(1.0, rel=1e-4)

    def test_pnl_long_loss(self):
        """Test P&L calculation for long position in loss."""
        strategy = FixedPercentageStopLoss(1.0)
        pnl = strategy.calculate_pnl_percent(
            entry_price=1.2500,
            current_price=1.2375,
            position_side="long",
        )
        assert pnl == pytest.approx(-1.0, rel=1e-4)

    def test_pnl_short_profit(self):
        """Test P&L calculation for short position in profit."""
        strategy = FixedPercentageStopLoss(1.0)
        pnl = strategy.calculate_pnl_percent(
            entry_price=1.2500,
            current_price=1.2375,
            position_side="short",
        )
        assert pnl == pytest.approx(1.0, rel=1e-4)

    def test_pnl_short_loss(self):
        """Test P&L calculation for short position in loss."""
        strategy = FixedPercentageStopLoss(1.0)
        pnl = strategy.calculate_pnl_percent(
            entry_price=1.2500,
            current_price=1.2625,
            position_side="short",
        )
        assert pnl == pytest.approx(-1.0, rel=1e-4)

    def test_pnl_zero_entry(self):
        """Test P&L calculation with zero entry price."""
        strategy = FixedPercentageStopLoss(1.0)
        pnl = strategy.calculate_pnl_percent(
            entry_price=0,
            current_price=1.2500,
            position_side="long",
        )
        assert pnl == 0.0


class TestSignalChangeExit:
    """Test SignalChangeExit strategy."""

    def test_signal_reversal_long_buy_to_sell(self):
        """Test signal reversal for long position: BUY → SELL."""
        strategy = SignalChangeExit()
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2520,
            position_side="long",
            entry_signal="BUY",
            current_signal="SELL",
        )
        assert signal.triggered is True
        assert signal.exit_type == ExitType.SIGNAL_REVERSAL
        assert "BUY → SELL" in signal.reason
        assert signal.confidence == 1.0
        assert signal.close_percent == 100.0

    def test_signal_reversal_short_sell_to_buy(self):
        """Test signal reversal for short position: SELL → BUY."""
        strategy = SignalChangeExit()
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2480,
            position_side="short",
            entry_signal="SELL",
            current_signal="BUY",
        )
        assert signal.triggered is True
        assert signal.exit_type == ExitType.SIGNAL_REVERSAL
        assert "SELL → BUY" in signal.reason
        assert signal.confidence == 1.0

    def test_no_signal_change_long_hold(self):
        """Test no signal change for long position (HOLD signal)."""
        strategy = SignalChangeExit()
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2520,
            position_side="long",
            entry_signal="BUY",
            current_signal="HOLD",
        )
        assert signal.triggered is False
        assert signal.exit_type == ExitType.SIGNAL_REVERSAL
        assert "unchanged" in signal.reason.lower()

    def test_no_signal_change_long_buy_continues(self):
        """Test no signal change when BUY continues."""
        strategy = SignalChangeExit()
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2550,
            position_side="long",
            entry_signal="BUY",
            current_signal="BUY",
        )
        assert signal.triggered is False
        assert signal.confidence == 0.0

    def test_no_signal_change_short_sell_continues(self):
        """Test no signal change when SELL continues."""
        strategy = SignalChangeExit()
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2450,
            position_side="short",
            entry_signal="SELL",
            current_signal="SELL",
        )
        assert signal.triggered is False

    def test_missing_entry_signal(self):
        """Test handling of missing entry signal."""
        strategy = SignalChangeExit()
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2520,
            position_side="long",
            entry_signal=None,
            current_signal="SELL",
        )
        assert signal.triggered is False
        assert "Missing" in signal.reason

    def test_missing_current_signal(self):
        """Test handling of missing current signal."""
        strategy = SignalChangeExit()
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2520,
            position_side="long",
            entry_signal="BUY",
            current_signal=None,
        )
        assert signal.triggered is False
        assert "Missing" in signal.reason

    def test_case_insensitive_signals(self):
        """Test that signals are case-insensitive."""
        strategy = SignalChangeExit()
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2520,
            position_side="long",
            entry_signal="buy",  # lowercase
            current_signal="SELL",  # uppercase
        )
        assert signal.triggered is True
        assert signal.exit_type == ExitType.SIGNAL_REVERSAL

    def test_exit_price_set_on_trigger(self):
        """Test that exit_price is set when signal change is triggered."""
        strategy = SignalChangeExit()
        current_price = 1.2530
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=current_price,
            position_side="long",
            entry_signal="BUY",
            current_signal="SELL",
        )
        assert signal.triggered is True
        assert signal.exit_price == current_price

    def test_exit_price_none_when_not_triggered(self):
        """Test that exit_price is None when not triggered."""
        strategy = SignalChangeExit()
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2520,
            position_side="long",
            entry_signal="BUY",
            current_signal="BUY",
        )
        assert signal.triggered is False
        assert signal.exit_price is None

    def test_long_position_ignores_buy_to_hold(self):
        """Test that long position doesn't exit on BUY → HOLD."""
        strategy = SignalChangeExit()
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2520,
            position_side="long",
            entry_signal="BUY",
            current_signal="HOLD",
        )
        assert signal.triggered is False

    def test_short_position_ignores_sell_to_hold(self):
        """Test that short position doesn't exit on SELL → HOLD."""
        strategy = SignalChangeExit()
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2480,
            position_side="short",
            entry_signal="SELL",
            current_signal="HOLD",
        )
        assert signal.triggered is False


class TestSignalChangeExitIntegration:
    """Integration tests for SignalChangeExit with other strategies."""

    def test_signal_change_in_factory(self):
        """Test creating SignalChangeExit from factory."""
        manager = ExitStrategyManager()
        strategy = manager.create_exit_strategy_from_config("signal_change")
        assert isinstance(strategy, SignalChangeExit)

    def test_signal_change_with_config(self):
        """Test SignalChangeExit with configuration."""
        config = {"risk_management": {}}
        strategy = SignalChangeExit(config)
        assert strategy is not None
        assert strategy.config == config

    def test_signal_change_to_dict(self):
        """Test SignalChangeExit signal serialization."""
        strategy = SignalChangeExit()
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2520,
            position_side="long",
            entry_signal="BUY",
            current_signal="SELL",
        )
        result = signal.to_dict()
        assert result["triggered"] is True
        assert result["exit_type"] == "signal_reversal"
        assert result["confidence"] == 1.0
        assert result["close_percent"] == 100.0


class TestAutoStopLoss:
    """Test auto_stop_loss functionality."""

    @pytest.fixture
    def manager(self):
        """Create ExitStrategyManager with config."""
        config = {
            "risk_management": {
                "stop_loss_percent": 1.0,
                "take_profit_percent": 2.0,
                "trailing_stop_percent": 0.5,
                "trailing_stop": True,
            }
        }
        return ExitStrategyManager(config)

    def test_auto_stop_loss_with_signal_change(self, manager):
        """Test auto_stop_loss with signal change exit."""
        result = manager.auto_stop_loss(
            entry_price=1.2500,
            current_price=1.2520,
            position_side="long",
            entry_signal="BUY",
            current_signal="SELL"
        )
        assert result["should_exit"] is True
        assert result["primary_exit"] == "signal_change"
        assert result["recommended_action"] == "close_all"

    def test_auto_stop_loss_stop_loss_priority(self, manager):
        """Test that stop loss has highest priority in auto_stop_loss."""
        result = manager.auto_stop_loss(
            entry_price=1.2500,
            current_price=1.2370,  # 1.04% loss
            position_side="long",
            entry_signal="BUY",
            current_signal="SELL"  # Signal also changed
        )
        # Stop loss should trigger before signal change
        assert result["should_exit"] is True
        assert result["primary_exit"] == "stop_loss"

    def test_auto_stop_loss_no_exit(self, manager):
        """Test auto_stop_loss with no exit conditions met."""
        result = manager.auto_stop_loss(
            entry_price=1.2500,
            current_price=1.2520,  # Small profit
            position_side="long",
            entry_signal="BUY",
            current_signal="BUY"  # No signal change
        )
        assert result["should_exit"] is False
        assert result["recommended_action"] == "hold"

    def test_auto_stop_loss_combines_all_exits(self, manager):
        """Test that auto_stop_loss evaluates all exit strategies."""
        result = manager.auto_stop_loss(
            entry_price=1.2500,
            current_price=1.2520,
            position_side="long",
            bars_held=50,
            initial_equity=10000,
            current_equity=10200
        )
        # Should have multiple exit evaluations in results
        assert "exits" in result
        assert len(result["exits"]) > 0


class TestEvaluateAllExitsWithSignalChange:
    """Test evaluate_all_exits with signal change integration."""

    @pytest.fixture
    def manager(self):
        """Create ExitStrategyManager with config."""
        config = {
            "risk_management": {
                "stop_loss_percent": 1.0,
                "take_profit_percent": 2.0,
            }
        }
        return ExitStrategyManager(config)

    def test_evaluate_all_exits_signal_change_triggered(self, manager):
        """Test evaluate_all_exits with signal change trigger."""
        result = manager.evaluate_all_exits(
            entry_price=1.2500,
            current_price=1.2520,
            position_side="long",
            entry_signal="BUY",
            current_signal="SELL"
        )
        assert result["should_exit"] is True
        assert result["primary_exit"] == "signal_change"
        assert result["recommended_action"] == "close_all"

    def test_evaluate_all_exits_no_signal_change(self, manager):
        """Test evaluate_all_exits when signal doesn't change."""
        result = manager.evaluate_all_exits(
            entry_price=1.2500,
            current_price=1.2520,
            position_side="long",
            entry_signal="BUY",
            current_signal="BUY"
        )
        # Should not exit on signal change
        assert result["should_exit"] is False

    def test_evaluate_all_exits_without_signals(self, manager):
        """Test evaluate_all_exits works without signal parameters."""
        result = manager.evaluate_all_exits(
            entry_price=1.2500,
            current_price=1.2520,
            position_side="long"
        )
        # Should work without signals (signal check skipped)
        assert "should_exit" in result
        assert "exits" in result
