"""Exit strategy utilities for position management.

Provides multiple exit strategies:
- ATR-based stops (volatility-adjusted)
- Trailing stops (profit protection)
- Time-based exits (hold duration limit)
- Breakeven exits (risk protection)
- Profit-taking levels (multi-level exits)
"""

import logging

import pandas as pd
import ta


class ExitStrategyManager:
    """Manages multiple exit strategies for positions."""

    def __init__(self, config=None):
        """Initialize exit strategy manager.

        Args:
            config: Configuration dict with exit strategy settings
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

    def atr_based_exit(self, data, entry_price, atr_multiplier=2.0):
        """Calculate ATR-based stop loss and take profit.

        Args:
            data: DataFrame with OHLC data
            entry_price: Entry price of the position
            atr_multiplier: Number of ATRs to use for stops (default 2.0)

        Returns:
            Dict with stop_loss and take_profit levels
        """
        try:
            atr = ta.volatility.AverageTrueRange(
                data["high"], data["low"], data["close"], window=14
            )
            latest_atr = atr.average_true_range().iloc[-1]

            stop_loss = entry_price - (latest_atr * atr_multiplier)
            take_profit = entry_price + (latest_atr * atr_multiplier * 1.5)

            return {
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "atr": latest_atr,
                "type": "ATR-based",
            }
        except Exception as e:
            self.logger.error("ATR exit calculation failed: %s", e)
            return None

    def trailing_stop_exit(self, data, entry_price, current_price, trail_percent=0.5):
        """Calculate trailing stop loss (profit protection).

        Args:
            data: DataFrame with OHLC data
            entry_price: Entry price of the position
            current_price: Current market price
            trail_percent: Trailing distance as % of entry price

        Returns:
            Dict with trailing stop level or None if stop not triggered
        """
        try:
            highest_price = data["high"].max()
            trailing_distance = highest_price * (trail_percent / 100)
            trailing_stop = highest_price - trailing_distance

            # Only return stop if price is above entry
            if current_price > entry_price:
                return {
                    "stop_loss": trailing_stop,
                    "highest_price": highest_price,
                    "distance_pct": trail_percent,
                    "type": "trailing_stop",
                }
            return None
        except Exception as e:
            self.logger.error("Trailing stop calculation failed: %s", e)
            return None

    def time_based_exit(self, bars_held, max_bars=100):
        """Check if position has been held too long.

        Args:
            bars_held: Number of bars the position has been open
            max_bars: Maximum bars to hold position (default 100)

        Returns:
            Bool indicating if time-based exit is triggered
        """
        return bars_held >= max_bars

    def breakeven_exit(self, entry_price, current_price, close_spread=0.001):
        """Check if position should close at breakeven (risk protection).

        Args:
            entry_price: Entry price of the position
            current_price: Current market price
            close_spread: Spread threshold for breakeven (default 0.001)

        Returns:
            Bool indicating if breakeven exit is triggered
        """
        return abs(current_price - entry_price) <= (entry_price * close_spread)

    def multi_level_exits(self, data, entry_price, position_size):
        """Calculate multi-level profit-taking strategy.

        Closes position in 3 levels:
        - 33% at 1x ATR
        - 33% at 2x ATR
        - 33% at 3x ATR

        Args:
            data: DataFrame with OHLC data
            entry_price: Entry price of the position
            position_size: Total position size

        Returns:
            List of exit levels with target prices and quantities
        """
        try:
            atr = ta.volatility.AverageTrueRange(
                data["high"], data["low"], data["close"], window=14
            )
            latest_atr = atr.average_true_range().iloc[-1]

            level_size = position_size / 3

            return [
                {
                    "level": 1,
                    "target": entry_price + (latest_atr * 1.0),
                    "quantity": level_size,
                    "pct_profit": 1.0 * (latest_atr / entry_price) * 100,
                },
                {
                    "level": 2,
                    "target": entry_price + (latest_atr * 2.0),
                    "quantity": level_size,
                    "pct_profit": 2.0 * (latest_atr / entry_price) * 100,
                },
                {
                    "level": 3,
                    "target": entry_price + (latest_atr * 3.0),
                    "quantity": level_size,
                    "pct_profit": 3.0 * (latest_atr / entry_price) * 100,
                },
            ]
        except Exception as e:
            self.logger.error("Multi-level exit calculation failed: %s", e)
            return []

    def combined_exit_strategy(
        self, data, entry_price, current_price, bars_held=0, position_size=0.01
    ):
        """Combined exit strategy using multiple criteria.

        Returns list of exit conditions that are currently triggered:
        1. Trailing stop (if in profit)
        2. Time-based exit (if held too long)
        3. Breakeven exit (if loss is minimal)
        4. ATR-based hard stops

        Args:
            data: DataFrame with OHLC data
            entry_price: Entry price
            current_price: Current price
            bars_held: Number of bars held (default 0)
            position_size: Position size for multi-level exits

        Returns:
            Dict with triggered exits and recommended action
        """
        exits_triggered = {
            "primary_exit": None,
            "all_exits": [],
            "recommended_action": "hold",
        }

        try:
            # Check trailing stop (best for profit protection)
            trailing = self.trailing_stop_exit(data, entry_price, current_price)
            if trailing and current_price >= entry_price:
                exits_triggered["all_exits"].append(trailing)
                exits_triggered["primary_exit"] = "trailing_stop"
                exits_triggered["recommended_action"] = "close_partial"

            # Check time-based exit
            if self.time_based_exit(bars_held, max_bars=100):
                exits_triggered["all_exits"].append({"type": "time_based"})
                if not exits_triggered["primary_exit"]:
                    exits_triggered["primary_exit"] = "time_based"
                exits_triggered["recommended_action"] = "close_partial"

            # Check breakeven exit (only if losing)
            if current_price < entry_price:
                if self.breakeven_exit(entry_price, current_price):
                    exits_triggered["all_exits"].append({"type": "breakeven"})
                    exits_triggered["primary_exit"] = "breakeven"
                    exits_triggered["recommended_action"] = "close_all"

            # ATR stops (hard stops - always calculate)
            atr_stops = self.atr_based_exit(data, entry_price)
            if atr_stops:
                exits_triggered["atr_stops"] = atr_stops
                if current_price <= atr_stops["stop_loss"]:
                    exits_triggered["all_exits"].append(atr_stops)
                    if not exits_triggered["primary_exit"]:
                        exits_triggered["primary_exit"] = "atr_stop"
                    exits_triggered["recommended_action"] = "close_all"

            return exits_triggered

        except Exception as e:
            self.logger.error("Combined exit strategy failed: %s", e)
            return exits_triggered
