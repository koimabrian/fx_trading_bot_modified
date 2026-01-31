# Exit Strategy Framework Documentation

## Overview

The FX Trading Bot provides a flexible, composable exit strategy framework that allows strategies to easily integrate any combination of exit logic. All exit strategies are built on the `BaseExitStrategy` abstract class and can be combined, configured via YAML, and optimized through backtesting.

## Architecture

### Abstract Base Class

```python
class BaseExitStrategy(ABC):
    """Abstract base class for all exit strategies."""
    
    @abstractmethod
    def evaluate(
        self,
        entry_price: float,
        current_price: float,
        position_side: str,
        **kwargs,
    ) -> ExitSignal:
        """Evaluate whether an exit condition is met."""
```

All exit strategies implement this interface, making them strategy-agnostic and reusable.

## Available Exit Strategies

### 1. Fixed Percentage Stop Loss (`FixedPercentageStopLoss`)

**Purpose**: Exit when loss exceeds a fixed percentage threshold.

**Parameters**:
- `stop_loss_percent` (float): Stop loss percentage (e.g., 1.0 for 1%)

**Usage**:
```python
from src.utils.exit_strategies import FixedPercentageStopLoss

strategy = FixedPercentageStopLoss(stop_loss_percent=1.0)
signal = strategy.evaluate(
    entry_price=1.2500,
    current_price=1.2370,  # 1.04% loss
    position_side="long"
)
# signal.triggered == True
```

**Config Example**:
```yaml
exit_strategies:
  - type: stop_loss
    params:
      sl_pct: 0.01  # 1% stop loss
```

---

### 2. Fixed Percentage Take Profit (`FixedPercentageTakeProfit`)

**Purpose**: Exit when profit reaches a fixed percentage target.

**Parameters**:
- `take_profit_percent` (float): Take profit percentage (e.g., 2.0 for 2%)

**Usage**:
```python
from src.utils.exit_strategies import FixedPercentageTakeProfit

strategy = FixedPercentageTakeProfit(take_profit_percent=2.0)
signal = strategy.evaluate(
    entry_price=1.2500,
    current_price=1.2760,  # 2.08% profit
    position_side="long"
)
# signal.triggered == True
```

**Config Example**:
```yaml
exit_strategies:
  - type: take_profit
    params:
      tp_pct: 0.02  # 2% take profit
```

---

### 3. Trailing Stop (`TrailingStopStrategy`)

**Purpose**: Lock in profits by trailing stop loss at a fixed distance from peak price.

**Parameters**:
- `trail_percent` (float): Trailing distance as percentage (e.g., 0.5 for 0.5%)
- `activation_percent` (float): Minimum profit % before trailing activates (default: 0.0 for immediate activation)

**Usage**:
```python
from src.utils.exit_strategies import TrailingStopStrategy

# Basic trailing stop (activates immediately)
strategy = TrailingStopStrategy(trail_percent=0.5)

# Trailing SL with activation threshold
strategy = TrailingStopStrategy(
    trail_percent=0.5,      # Trail by 0.5%
    activation_percent=1.0  # Only activate after +1% profit
)

signal = strategy.evaluate(
    entry_price=1.2500,
    current_price=1.2550,
    position_side="long",
    highest_price=1.2620  # Peak price since entry
)
# Trailing stop at 1.2620 * (1 - 0.5/100) = 1.2557
# signal.triggered == True (current 1.2550 < 1.2557)
```

**Config Example**:
```yaml
exit_strategies:
  # Basic trailing stop
  - type: trailing_stop
    params:
      trail_pct: 0.005  # 0.5% trailing distance

  # Trailing SL with activation threshold
  - type: trailing_sl
    params:
      activate_pct: 0.05  # Activate after +5% profit
      trail_pct: 0.02     # Trail by 2% once activated
```

**Key Features**:
- Automatically tracks highest/lowest price per position
- Supports position-specific tracking via `position_id`
- Can reset tracking with `reset_tracking(position_id)`

---

### 4. Equity Target Exit (`EquityTargetExit`)

**Purpose**: Exit all positions when account equity increases by target percentage.

**Parameters**:
- `target_equity_increase_percent` (float): Target equity increase % (e.g., 5.0 for 5%)

**Usage**:
```python
from src.utils.exit_strategies import EquityTargetExit

strategy = EquityTargetExit(target_equity_increase_percent=5.0)
signal = strategy.evaluate(
    entry_price=0,  # Not used
    current_price=0,  # Not used
    position_side="long",
    initial_equity=10000,
    current_equity=10600  # 6% increase
)
# signal.triggered == True
# signal.close_percent == 100.0 (close all positions)
```

**Config Example**:
```yaml
exit_strategies:
  - type: equity_percent
    params:
      pct: 5  # Exit when account grows by 5%
```

---

### 5. Signal Change Exit (`SignalChangeExit`) ⭐ NEW

**Purpose**: Exit when trading signal reverses (BUY→SELL or SELL→BUY).

**Parameters**: None (uses signal comparison)

**Usage**:
```python
from src.utils.exit_strategies import SignalChangeExit

strategy = SignalChangeExit()
signal = strategy.evaluate(
    entry_price=1.2500,
    current_price=1.2520,
    position_side="long",
    entry_signal="BUY",    # Signal that opened position
    current_signal="SELL"  # Current market signal
)
# signal.triggered == True (BUY → SELL reversal)
# signal.close_percent == 100.0 (close entire position)
```

**Config Example**:
```yaml
exit_strategies:
  - type: signal_change
    params: {}  # No parameters needed
```

**Behavior**:
- **Long positions** (entered on BUY): Exit when signal changes to SELL
- **Short positions** (entered on SELL): Exit when signal changes to BUY
- **HOLD signals**: Do not trigger exits (allows consolidation)
- **Case-insensitive**: Handles "buy", "BUY", "Buy" equivalently
- **Missing signals**: Returns `triggered=False` with error reason

---

## Using Exit Strategies in Your Trading Strategy

### Method 1: Direct Instantiation

```python
from src.utils.exit_strategies import (
    FixedPercentageStopLoss,
    FixedPercentageTakeProfit,
    SignalChangeExit
)

class MyStrategy(BaseStrategy):
    def __init__(self):
        self.stop_loss = FixedPercentageStopLoss(1.0)
        self.take_profit = FixedPercentageTakeProfit(2.0)
        self.signal_exit = SignalChangeExit()
    
    def check_exit(self, position, current_price, current_signal):
        # Check all exit conditions
        sl_signal = self.stop_loss.evaluate(
            entry_price=position['entry_price'],
            current_price=current_price,
            position_side=position['side']
        )
        
        tp_signal = self.take_profit.evaluate(
            entry_price=position['entry_price'],
            current_price=current_price,
            position_side=position['side']
        )
        
        sig_signal = self.signal_exit.evaluate(
            entry_price=position['entry_price'],
            current_price=current_price,
            position_side=position['side'],
            entry_signal=position['entry_signal'],
            current_signal=current_signal
        )
        
        # Priority: SL > TP > Signal Change
        if sl_signal.triggered:
            return sl_signal
        elif tp_signal.triggered:
            return tp_signal
        elif sig_signal.triggered:
            return sig_signal
        
        return None
```

### Method 2: Using ExitStrategyManager

```python
from src.utils.exit_strategies import ExitStrategyManager

config = {
    'risk_management': {
        'stop_loss_percent': 1.0,
        'take_profit_percent': 2.0,
        'trailing_stop_percent': 0.5,
        'trailing_activation_percent': 1.0,
        'equity_target_percent': 5.0
    }
}

manager = ExitStrategyManager(config)

# Evaluate all exits at once
result = manager.evaluate_all_exits(
    entry_price=1.2500,
    current_price=1.2520,
    position_side="long",
    bars_held=50,
    initial_equity=10000,
    current_equity=10300
)

if result['should_exit']:
    print(f"Exit triggered: {result['primary_exit']}")
    print(f"Action: {result['recommended_action']}")
```

### Method 3: Factory Pattern from Config

```python
manager = ExitStrategyManager(config)

# Create strategies dynamically
sl_strategy = manager.create_exit_strategy_from_config("stop_loss")
tp_strategy = manager.create_exit_strategy_from_config("take_profit")
trail_strategy = manager.create_exit_strategy_from_config("trailing_stop")
signal_strategy = manager.create_exit_strategy_from_config("signal_change")
```

---

## Configuration via YAML

### Complete Configuration Example

```yaml
# src/config/config.yaml
risk_management:
  stop_loss_percent: 1.0           # 1% stop loss
  take_profit_percent: 2.0         # 2% take profit
  trailing_stop: true              # Enable trailing
  trailing_stop_percent: 0.5       # 0.5% trailing distance
  trailing_activation_percent: 1.0 # Activate after +1% profit
  equity_target_percent: 5.0       # 5% account growth target
  max_hold_bars: 100               # Time-based exit
  use_atr_stops: true              # ATR-based dynamic stops

# Exit strategies can also be defined separately for flexibility
exit_strategies:
  - type: stop_loss
    params:
      sl_pct: 0.01
  - type: take_profit
    params:
      tp_pct: 0.02
  - type: trailing_sl
    params:
      activate_pct: 0.05
      trail_pct: 0.02
  - type: equity_percent
    params:
      pct: 5
  - type: signal_change
    params: {}
```

---

## Combining Exit Strategies

Exit strategies are evaluated in **priority order**:

1. **Stop Loss** (highest priority - protects capital)
2. **Take Profit** (locks in gains)
3. **Trailing Stop** (profit protection)
4. **Time-Based** (prevents indefinite holds)
5. **Equity Target** (daily profit target)
6. **Signal Change** (strategy reversal)
7. **ATR-Based** (volatility-adjusted stops)

### Custom Combination Example

```python
class CustomExitManager:
    def __init__(self):
        self.sl = FixedPercentageStopLoss(1.0)
        self.tp = FixedPercentageTakeProfit(2.0)
        self.trail = TrailingStopStrategy(0.5, activation_percent=1.5)
        self.signal = SignalChangeExit()
    
    def evaluate_exits(self, position, market_data, current_signal):
        exits = []
        
        # Evaluate all strategies
        exits.append(self.sl.evaluate(...))
        exits.append(self.tp.evaluate(...))
        exits.append(self.trail.evaluate(...))
        exits.append(self.signal.evaluate(..., current_signal=current_signal))
        
        # Return first triggered exit (priority order)
        for exit_signal in exits:
            if exit_signal.triggered:
                return exit_signal
        
        return None
```

---

## Best Practices

### 1. **Always Use Stop Loss**
Never enter a position without a stop loss. Use `FixedPercentageStopLoss` or ATR-based stops.

### 2. **Combine Multiple Exits**
Use SL + TP + Trailing for comprehensive risk management.

### 3. **Trailing SL Activation**
Set `activation_percent > 0` to avoid premature trailing on minor retracements.

### 4. **Signal Change for Reversal Strategies**
Use `SignalChangeExit` for mean-reversion or oscillator-based strategies.

### 5. **Test Edge Cases**
- Price gaps past stop loss
- Simultaneous exit triggers
- Missing or invalid data
- Extreme volatility scenarios

### 6. **Parameter Ranges**
Recommended starting values:
- **Stop Loss**: 0.5% - 2.0%
- **Take Profit**: 1.5% - 3.0%
- **Trailing Distance**: 0.3% - 1.0%
- **Trailing Activation**: 0.0% - 2.0%
- **Equity Target**: 2% - 5% daily

---

## References

- **Source Code**: `src/utils/exit_strategies.py`
- **Tests**: `tests/unit/test_exit_strategies.py`
- **Config Example**: `src/config/config.yaml`

---

## Change Log

### v1.1.0 (2026-01-31)
- ✅ Added `SignalChangeExit` strategy
- ✅ Enhanced documentation with usage examples
- ✅ Added comprehensive unit tests (75/75 passing)
- ✅ Updated config.yaml with exit_strategies section

### v1.0.0 (Initial)
- ✅ `FixedPercentageStopLoss`
- ✅ `FixedPercentageTakeProfit`
- ✅ `TrailingStopStrategy` (with activation threshold)
- ✅ `EquityTargetExit`
- ✅ `ExitStrategyManager` (unified interface)
