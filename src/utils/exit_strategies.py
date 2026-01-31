"""Exit strategy utilities for position management.

Provides multiple exit strategies:
- ATR-based stops (volatility-adjusted)
- Trailing stops (profit protection)
- Time-based exits (hold duration limit)
- Breakeven exits (risk protection)
- Profit-taking levels (multi-level exits)
- Fixed percentage stop loss/take profit
- Account equity % target exits
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Union

import pandas as pd
import ta


class ExitType(Enum):
    """Enumeration of exit strategy types."""

    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TRAILING_STOP = "trailing_stop"
    TIME_BASED = "time_based"
    BREAKEVEN = "breakeven"
    ATR_BASED = "atr_based"
    EQUITY_TARGET = "equity_target"
    SIGNAL_REVERSAL = "signal_reversal"


@dataclass
class ExitSignal:
    """Represents an exit signal from an exit strategy.

    Attributes:
        triggered: Whether the exit condition is triggered
        exit_type: Type of exit (from ExitType enum)
        exit_price: Recommended exit price (if applicable)
        reason: Human-readable reason for the exit
        confidence: Confidence level of the exit signal (0.0-1.0)
        close_percent: Percentage of position to close (0-100)
    """

    triggered: bool
    exit_type: ExitType
    exit_price: Optional[float] = None
    reason: str = ""
    confidence: float = 1.0
    close_percent: float = 100.0

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "triggered": self.triggered,
            "exit_type": self.exit_type.value,
            "exit_price": self.exit_price,
            "reason": self.reason,
            "confidence": self.confidence,
            "close_percent": self.close_percent,
        }


class BaseExitStrategy(ABC):
    """Abstract base class for all exit strategies.

    This class defines the interface that all exit strategies must implement,
    making exit strategies strategy-agnostic and reusable across different
    trading strategies.
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize the exit strategy.

        Args:
            config: Configuration dictionary with strategy-specific settings
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def evaluate(
        self,
        entry_price: float,
        current_price: float,
        position_side: str,
        **kwargs,
    ) -> ExitSignal:
        """Evaluate whether an exit condition is met.

        Args:
            entry_price: Price at which position was entered
            current_price: Current market price
            position_side: 'long' or 'short'
            **kwargs: Additional parameters specific to the strategy

        Returns:
            ExitSignal with evaluation results
        """

    def calculate_pnl_percent(
        self, entry_price: float, current_price: float, position_side: str
    ) -> float:
        """Calculate profit/loss as a percentage.

        Args:
            entry_price: Entry price of position
            current_price: Current market price
            position_side: 'long' or 'short'

        Returns:
            P&L as percentage (positive = profit, negative = loss)
        """
        if entry_price <= 0:
            return 0.0

        if position_side.lower() == "long":
            return ((current_price - entry_price) / entry_price) * 100
        else:  # short
            return ((entry_price - current_price) / entry_price) * 100


class FixedPercentageStopLoss(BaseExitStrategy):
    """Fixed percentage stop loss exit strategy."""

    def __init__(self, stop_loss_percent: float = 1.0, config: Optional[Dict] = None):
        """Initialize fixed percentage stop loss.

        Args:
            stop_loss_percent: Stop loss percentage (e.g., 1.0 for 1%)
            config: Additional configuration
        """
        super().__init__(config)
        self.stop_loss_percent = stop_loss_percent

    def evaluate(
        self,
        entry_price: float,
        current_price: float,
        position_side: str,
        **kwargs,
    ) -> ExitSignal:
        """Check if stop loss is triggered."""
        pnl_pct = self.calculate_pnl_percent(entry_price, current_price, position_side)

        # Stop loss triggers when loss exceeds threshold
        triggered = pnl_pct <= -self.stop_loss_percent

        if position_side.lower() == "long":
            exit_price = entry_price * (1 - self.stop_loss_percent / 100)
        else:
            exit_price = entry_price * (1 + self.stop_loss_percent / 100)

        return ExitSignal(
            triggered=triggered,
            exit_type=ExitType.STOP_LOSS,
            exit_price=exit_price,
            reason=f"Fixed SL at {self.stop_loss_percent}% (current: {pnl_pct:.2f}%)",
            confidence=1.0 if triggered else 0.0,
        )


class FixedPercentageTakeProfit(BaseExitStrategy):
    """Fixed percentage take profit exit strategy."""

    def __init__(
        self, take_profit_percent: float = 2.0, config: Optional[Dict] = None
    ):
        """Initialize fixed percentage take profit.

        Args:
            take_profit_percent: Take profit percentage (e.g., 2.0 for 2%)
            config: Additional configuration
        """
        super().__init__(config)
        self.take_profit_percent = take_profit_percent

    def evaluate(
        self,
        entry_price: float,
        current_price: float,
        position_side: str,
        **kwargs,
    ) -> ExitSignal:
        """Check if take profit is triggered."""
        pnl_pct = self.calculate_pnl_percent(entry_price, current_price, position_side)

        # Take profit triggers when profit exceeds threshold
        triggered = pnl_pct >= self.take_profit_percent

        if position_side.lower() == "long":
            exit_price = entry_price * (1 + self.take_profit_percent / 100)
        else:
            exit_price = entry_price * (1 - self.take_profit_percent / 100)

        return ExitSignal(
            triggered=triggered,
            exit_type=ExitType.TAKE_PROFIT,
            exit_price=exit_price,
            reason=f"Fixed TP at {self.take_profit_percent}% (current: {pnl_pct:.2f}%)",
            confidence=1.0 if triggered else 0.0,
        )


class TrailingStopStrategy(BaseExitStrategy):
    """Trailing stop loss exit strategy with configurable options."""

    def __init__(
        self,
        trail_percent: float = 0.5,
        activation_percent: float = 0.0,
        config: Optional[Dict] = None,
    ):
        """Initialize trailing stop.

        Args:
            trail_percent: Trailing distance as percentage
            activation_percent: Minimum profit % before trailing activates (0 = immediate)
            config: Additional configuration
        """
        super().__init__(config)
        self.trail_percent = trail_percent
        self.activation_percent = activation_percent
        self._highest_price: Dict[str, float] = {}  # Track per position

    def evaluate(
        self,
        entry_price: float,
        current_price: float,
        position_side: str,
        position_id: str = "default",
        highest_price: Optional[float] = None,
        **kwargs,
    ) -> ExitSignal:
        """Check if trailing stop is triggered.

        Args:
            entry_price: Entry price
            current_price: Current market price
            position_side: 'long' or 'short'
            position_id: Unique position identifier for tracking
            highest_price: Optionally pass the highest/lowest price since entry
        """
        pnl_pct = self.calculate_pnl_percent(entry_price, current_price, position_side)

        # Check if trailing is activated (requires minimum profit)
        if pnl_pct < self.activation_percent:
            return ExitSignal(
                triggered=False,
                exit_type=ExitType.TRAILING_STOP,
                reason=f"Trailing not active (need {self.activation_percent}% profit)",
            )

        # Update highest/lowest price tracking
        if position_side.lower() == "long":
            if highest_price is not None:
                peak_price = highest_price
            else:
                peak_price = self._highest_price.get(position_id, current_price)
                if current_price > peak_price:
                    peak_price = current_price
                    self._highest_price[position_id] = peak_price

            trailing_stop = peak_price * (1 - self.trail_percent / 100)
            triggered = current_price <= trailing_stop
        else:
            # For shorts, track lowest price and trail upward
            if highest_price is not None:
                peak_price = highest_price
            else:
                peak_price = self._highest_price.get(position_id, current_price)
                if current_price < peak_price:
                    peak_price = current_price
                    self._highest_price[position_id] = peak_price

            trailing_stop = peak_price * (1 + self.trail_percent / 100)
            triggered = current_price >= trailing_stop

        return ExitSignal(
            triggered=triggered,
            exit_type=ExitType.TRAILING_STOP,
            exit_price=trailing_stop,
            reason=f"Trailing stop at {self.trail_percent}% from peak {peak_price:.5f}",
            confidence=1.0 if triggered else 0.5,
        )

    def reset_tracking(self, position_id: str = None):
        """Reset highest/lowest price tracking.

        Args:
            position_id: Specific position to reset, or None for all
        """
        if position_id:
            self._highest_price.pop(position_id, None)
        else:
            self._highest_price.clear()


class EquityTargetExit(BaseExitStrategy):
    """Exit strategy based on account equity percentage increase.

    Triggers an exit when account equity has increased by a target percentage.
    """

    def __init__(
        self,
        target_equity_increase_percent: float = 5.0,
        config: Optional[Dict] = None,
    ):
        """Initialize equity target exit.

        Args:
            target_equity_increase_percent: Target equity increase % to trigger exit
            config: Additional configuration
        """
        super().__init__(config)
        self.target_equity_increase_percent = target_equity_increase_percent

    def evaluate(
        self,
        entry_price: float,
        current_price: float,
        position_side: str,
        initial_equity: float = 0.0,
        current_equity: float = 0.0,
        **kwargs,
    ) -> ExitSignal:
        """Check if equity target is reached.

        Args:
            entry_price: Entry price (used for consistency with interface)
            current_price: Current price (used for consistency with interface)
            position_side: Position side
            initial_equity: Account equity at start of trading session
            current_equity: Current account equity
        """
        if initial_equity <= 0 or current_equity <= 0:
            return ExitSignal(
                triggered=False,
                exit_type=ExitType.EQUITY_TARGET,
                reason="Invalid equity values provided",
            )

        equity_change_pct = ((current_equity - initial_equity) / initial_equity) * 100
        triggered = equity_change_pct >= self.target_equity_increase_percent

        return ExitSignal(
            triggered=triggered,
            exit_type=ExitType.EQUITY_TARGET,
            reason=f"Equity target {self.target_equity_increase_percent}% "
            f"(current: {equity_change_pct:.2f}%)",
            confidence=1.0 if triggered else equity_change_pct
            / self.target_equity_increase_percent,
            close_percent=100.0,  # Close all positions when equity target hit
        )


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

    def fixed_stop_loss_exit(
        self,
        entry_price: float,
        current_price: float,
        position_side: str = "long",
        stop_loss_percent: float = 1.0,
    ) -> Dict:
        """Calculate fixed percentage stop loss.

        Args:
            entry_price: Entry price of the position
            current_price: Current market price
            position_side: 'long' or 'short'
            stop_loss_percent: Stop loss percentage (default 1.0%)

        Returns:
            Dict with stop loss details and trigger status
        """
        strategy = FixedPercentageStopLoss(stop_loss_percent)
        signal = strategy.evaluate(entry_price, current_price, position_side)
        return signal.to_dict()

    def fixed_take_profit_exit(
        self,
        entry_price: float,
        current_price: float,
        position_side: str = "long",
        take_profit_percent: float = 2.0,
    ) -> Dict:
        """Calculate fixed percentage take profit.

        Args:
            entry_price: Entry price of the position
            current_price: Current market price
            position_side: 'long' or 'short'
            take_profit_percent: Take profit percentage (default 2.0%)

        Returns:
            Dict with take profit details and trigger status
        """
        strategy = FixedPercentageTakeProfit(take_profit_percent)
        signal = strategy.evaluate(entry_price, current_price, position_side)
        return signal.to_dict()

    def equity_target_exit(
        self,
        initial_equity: float,
        current_equity: float,
        target_percent: float = 5.0,
    ) -> Dict:
        """Check if account equity target has been reached.

        Args:
            initial_equity: Account equity at session start
            current_equity: Current account equity
            target_percent: Target equity increase percentage

        Returns:
            Dict with equity target details and trigger status
        """
        strategy = EquityTargetExit(target_percent)
        signal = strategy.evaluate(
            entry_price=0,  # Not used for equity target
            current_price=0,  # Not used for equity target
            position_side="long",  # Not used for equity target
            initial_equity=initial_equity,
            current_equity=current_equity,
        )
        return signal.to_dict()

    def advanced_trailing_stop(
        self,
        entry_price: float,
        current_price: float,
        position_side: str = "long",
        trail_percent: float = 0.5,
        activation_percent: float = 0.0,
        highest_price: Optional[float] = None,
        position_id: str = "default",
    ) -> Dict:
        """Calculate advanced trailing stop with activation threshold.

        Args:
            entry_price: Entry price of the position
            current_price: Current market price
            position_side: 'long' or 'short'
            trail_percent: Trailing distance percentage
            activation_percent: Min profit % before trailing activates
            highest_price: Highest/lowest price since entry (optional)
            position_id: Unique position identifier

        Returns:
            Dict with trailing stop details and trigger status
        """
        strategy = TrailingStopStrategy(trail_percent, activation_percent)
        signal = strategy.evaluate(
            entry_price,
            current_price,
            position_side,
            position_id=position_id,
            highest_price=highest_price,
        )
        return signal.to_dict()

    def evaluate_all_exits(
        self,
        entry_price: float,
        current_price: float,
        position_side: str = "long",
        data: Optional[pd.DataFrame] = None,
        bars_held: int = 0,
        initial_equity: float = 0.0,
        current_equity: float = 0.0,
        config: Optional[Dict] = None,
    ) -> Dict:
        """Evaluate all exit strategies and return comprehensive results.

        This method provides a unified interface for evaluating multiple exit
        strategies at once, making it strategy-agnostic and suitable for use
        by any trading strategy.

        Args:
            entry_price: Entry price of the position
            current_price: Current market price
            position_side: 'long' or 'short'
            data: DataFrame with OHLC data (for ATR calculations)
            bars_held: Number of bars position has been held
            initial_equity: Account equity at session start
            current_equity: Current account equity
            config: Optional config override for exit strategy parameters

        Returns:
            Dict with all exit evaluations and recommended action
        """
        cfg = config or self.config.get("risk_management", {})

        # Get parameters from config
        sl_pct = cfg.get("stop_loss_percent", 1.0)
        tp_pct = cfg.get("take_profit_percent", 2.0)
        trailing_pct = cfg.get("trailing_stop_percent", 0.5)
        use_trailing = cfg.get("trailing_stop", True)
        max_bars = cfg.get("max_hold_bars", 100)
        equity_target = cfg.get("equity_target_percent", 5.0)

        results = {
            "exits": [],
            "primary_exit": None,
            "recommended_action": "hold",
            "should_exit": False,
        }

        try:
            # 1. Check fixed stop loss
            sl_result = self.fixed_stop_loss_exit(
                entry_price, current_price, position_side, sl_pct
            )
            results["exits"].append(sl_result)
            if sl_result["triggered"]:
                results["primary_exit"] = "stop_loss"
                results["recommended_action"] = "close_all"
                results["should_exit"] = True
                return results  # Stop loss takes priority

            # 2. Check fixed take profit
            tp_result = self.fixed_take_profit_exit(
                entry_price, current_price, position_side, tp_pct
            )
            results["exits"].append(tp_result)
            if tp_result["triggered"]:
                results["primary_exit"] = "take_profit"
                results["recommended_action"] = "close_all"
                results["should_exit"] = True
                return results

            # 3. Check trailing stop (if enabled)
            if use_trailing:
                trail_result = self.advanced_trailing_stop(
                    entry_price, current_price, position_side, trailing_pct
                )
                results["exits"].append(trail_result)
                if trail_result["triggered"]:
                    results["primary_exit"] = "trailing_stop"
                    results["recommended_action"] = "close_all"
                    results["should_exit"] = True
                    return results

            # 4. Check time-based exit
            if self.time_based_exit(bars_held, max_bars):
                results["exits"].append(
                    {"triggered": True, "exit_type": "time_based", "reason": f"Held {bars_held} bars (max: {max_bars})"}
                )
                results["primary_exit"] = "time_based"
                results["recommended_action"] = "close_partial"
                results["should_exit"] = True

            # 5. Check equity target
            if initial_equity > 0 and current_equity > 0:
                equity_result = self.equity_target_exit(
                    initial_equity, current_equity, equity_target
                )
                results["exits"].append(equity_result)
                if equity_result["triggered"]:
                    results["primary_exit"] = "equity_target"
                    results["recommended_action"] = "close_all"
                    results["should_exit"] = True

            # 6. Check ATR-based exits (if data provided)
            if data is not None and not data.empty:
                atr_result = self.atr_based_exit(data, entry_price)
                if atr_result:
                    # Check if stop is hit
                    if position_side.lower() == "long":
                        if current_price <= atr_result["stop_loss"]:
                            results["exits"].append(
                                {"triggered": True, "exit_type": "atr_stop", **atr_result}
                            )
                            if not results["should_exit"]:
                                results["primary_exit"] = "atr_stop"
                                results["recommended_action"] = "close_all"
                                results["should_exit"] = True
                    else:
                        # For short positions, ATR stop is above entry
                        atr_short_stop = entry_price + atr_result["atr"] * 2.0
                        if current_price >= atr_short_stop:
                            results["exits"].append(
                                {"triggered": True, "exit_type": "atr_stop", "stop_loss": atr_short_stop}
                            )
                            if not results["should_exit"]:
                                results["primary_exit"] = "atr_stop"
                                results["recommended_action"] = "close_all"
                                results["should_exit"] = True

        except Exception as e:
            self.logger.error("Error evaluating exits: %s", e)

        return results

    def create_exit_strategy_from_config(
        self, strategy_type: str, config: Optional[Dict] = None
    ) -> Optional[BaseExitStrategy]:
        """Factory method to create exit strategy instances from configuration.

        Args:
            strategy_type: Type of exit strategy ('stop_loss', 'take_profit',
                          'trailing_stop', 'equity_target')
            config: Configuration dict with strategy parameters

        Returns:
            Exit strategy instance or None if type not recognized
        """
        cfg = config or self.config.get("risk_management", {})

        strategy_map = {
            "stop_loss": lambda: FixedPercentageStopLoss(
                cfg.get("stop_loss_percent", 1.0)
            ),
            "take_profit": lambda: FixedPercentageTakeProfit(
                cfg.get("take_profit_percent", 2.0)
            ),
            "trailing_stop": lambda: TrailingStopStrategy(
                cfg.get("trailing_stop_percent", 0.5),
                cfg.get("trailing_activation_percent", 0.0),
            ),
            "equity_target": lambda: EquityTargetExit(
                cfg.get("equity_target_percent", 5.0)
            ),
        }

        factory_fn = strategy_map.get(strategy_type.lower())
        if factory_fn:
            return factory_fn()

        self.logger.warning("Unknown exit strategy type: %s", strategy_type)
        return None
