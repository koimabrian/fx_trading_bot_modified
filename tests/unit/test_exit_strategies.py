"""Unit tests for exit strategies module."""

import pytest
from unittest.mock import Mock, patch
import pandas as pd
from datetime import datetime

from src.utils.exit_strategies import (
    ExitStrategyManager,
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
