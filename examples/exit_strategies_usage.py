#!/usr/bin/env python3
"""
Example usage of the Exit Strategy Framework.

This script demonstrates how to use all available exit strategies
including the new SignalChangeExit.
"""

from src.utils.exit_strategies import (
    FixedPercentageStopLoss,
    FixedPercentageTakeProfit,
    TrailingStopStrategy,
    EquityTargetExit,
    SignalChangeExit,
    ExitStrategyManager,
)


def example_1_direct_usage():
    """Example 1: Direct instantiation of exit strategies."""
    print("\n" + "="*60)
    print("Example 1: Direct Usage of Exit Strategies")
    print("="*60)
    
    # Create strategies
    stop_loss = FixedPercentageStopLoss(stop_loss_percent=1.0)
    take_profit = FixedPercentageTakeProfit(take_profit_percent=2.0)
    trailing = TrailingStopStrategy(trail_percent=0.5, activation_percent=1.0)
    signal_exit = SignalChangeExit()
    
    # Simulate a losing trade
    print("\nScenario: Long position with 1.5% loss")
    sl_signal = stop_loss.evaluate(
        entry_price=1.2500,
        current_price=1.2313,  # 1.5% loss
        position_side="long"
    )
    print(f"Stop Loss Triggered: {sl_signal.triggered}")
    print(f"Reason: {sl_signal.reason}")
    
    # Simulate a winning trade
    print("\nScenario: Long position with 2.5% profit")
    tp_signal = take_profit.evaluate(
        entry_price=1.2500,
        current_price=1.2813,  # 2.5% profit
        position_side="long"
    )
    print(f"Take Profit Triggered: {tp_signal.triggered}")
    print(f"Reason: {tp_signal.reason}")
    
    # Simulate signal reversal
    print("\nScenario: Long position with signal reversal BUY→SELL")
    sig_signal = signal_exit.evaluate(
        entry_price=1.2500,
        current_price=1.2520,
        position_side="long",
        entry_signal="BUY",
        current_signal="SELL"
    )
    print(f"Signal Change Triggered: {sig_signal.triggered}")
    print(f"Reason: {sig_signal.reason}")
    print(f"Exit Price: {sig_signal.exit_price}")


def example_2_trailing_stop():
    """Example 2: Trailing stop with activation threshold."""
    print("\n" + "="*60)
    print("Example 2: Trailing Stop with Activation")
    print("="*60)
    
    # Trailing stop that only activates after +1% profit
    trailing = TrailingStopStrategy(
        trail_percent=0.5,      # Trail by 0.5%
        activation_percent=1.0  # Only activate after +1% profit
    )
    
    entry_price = 1.2500
    
    # Test 1: Small profit (0.4%) - trailing not activated
    print("\nTest 1: 0.4% profit - Trailing not activated")
    signal = trailing.evaluate(
        entry_price=entry_price,
        current_price=1.2550,  # 0.4% profit
        position_side="long"
    )
    print(f"Triggered: {signal.triggered}")
    print(f"Reason: {signal.reason}")
    
    # Test 2: Good profit (2%) - trailing activated but not hit
    print("\nTest 2: 2% profit - Trailing activated, not hit")
    signal = trailing.evaluate(
        entry_price=entry_price,
        current_price=1.2750,  # 2% profit
        position_side="long",
        highest_price=1.2750
    )
    print(f"Triggered: {signal.triggered}")
    print(f"Reason: {signal.reason}")
    
    # Test 3: Retracement hits trailing stop
    print("\nTest 3: Retracement hits trailing stop")
    signal = trailing.evaluate(
        entry_price=entry_price,
        current_price=1.2690,  # Retraced from 1.2750
        position_side="long",
        highest_price=1.2750  # Peak was 1.2750
    )
    # Trailing stop at 1.2750 * (1 - 0.5/100) = 1.2686
    print(f"Triggered: {signal.triggered}")
    print(f"Reason: {signal.reason}")
    print(f"Exit Price: {signal.exit_price}")


def example_3_manager_usage():
    """Example 3: Using ExitStrategyManager."""
    print("\n" + "="*60)
    print("Example 3: Using ExitStrategyManager")
    print("="*60)
    
    config = {
        'risk_management': {
            'stop_loss_percent': 1.0,
            'take_profit_percent': 2.0,
            'trailing_stop_percent': 0.5,
            'trailing_activation_percent': 1.0,
            'equity_target_percent': 5.0,
            'max_hold_bars': 100,
        }
    }
    
    manager = ExitStrategyManager(config)
    
    # Scenario: Stop loss hit
    print("\nScenario: Position with 1.5% loss")
    result = manager.evaluate_all_exits(
        entry_price=1.2500,
        current_price=1.2313,  # 1.5% loss
        position_side="long",
        bars_held=30
    )
    print(f"Should Exit: {result['should_exit']}")
    print(f"Primary Exit: {result['primary_exit']}")
    print(f"Recommended Action: {result['recommended_action']}")


def example_4_factory_pattern():
    """Example 4: Creating strategies from factory."""
    print("\n" + "="*60)
    print("Example 4: Factory Pattern")
    print("="*60)
    
    config = {
        'risk_management': {
            'stop_loss_percent': 1.0,
            'take_profit_percent': 2.0,
            'trailing_stop_percent': 0.5,
        }
    }
    
    manager = ExitStrategyManager(config)
    
    # Create strategies dynamically
    strategies = {
        'stop_loss': manager.create_exit_strategy_from_config('stop_loss'),
        'take_profit': manager.create_exit_strategy_from_config('take_profit'),
        'trailing_stop': manager.create_exit_strategy_from_config('trailing_stop'),
        'signal_change': manager.create_exit_strategy_from_config('signal_change'),
    }
    
    print("\nCreated strategies:")
    for name, strategy in strategies.items():
        print(f"  - {name}: {type(strategy).__name__}")


def example_5_signal_change_scenarios():
    """Example 5: Comprehensive signal change scenarios."""
    print("\n" + "="*60)
    print("Example 5: Signal Change Exit Scenarios")
    print("="*60)
    
    strategy = SignalChangeExit()
    
    scenarios = [
        {
            "name": "Long BUY→SELL reversal",
            "position_side": "long",
            "entry_signal": "BUY",
            "current_signal": "SELL",
            "expected": True
        },
        {
            "name": "Long BUY→BUY continues",
            "position_side": "long",
            "entry_signal": "BUY",
            "current_signal": "BUY",
            "expected": False
        },
        {
            "name": "Long BUY→HOLD consolidates",
            "position_side": "long",
            "entry_signal": "BUY",
            "current_signal": "HOLD",
            "expected": False
        },
        {
            "name": "Short SELL→BUY reversal",
            "position_side": "short",
            "entry_signal": "SELL",
            "current_signal": "BUY",
            "expected": True
        },
        {
            "name": "Case insensitive (buy→SELL)",
            "position_side": "long",
            "entry_signal": "buy",
            "current_signal": "SELL",
            "expected": True
        },
    ]
    
    for scenario in scenarios:
        signal = strategy.evaluate(
            entry_price=1.2500,
            current_price=1.2520,
            position_side=scenario["position_side"],
            entry_signal=scenario["entry_signal"],
            current_signal=scenario["current_signal"]
        )
        status = "✅" if signal.triggered == scenario["expected"] else "❌"
        print(f"\n{status} {scenario['name']}")
        print(f"   Triggered: {signal.triggered} (expected: {scenario['expected']})")
        print(f"   Reason: {signal.reason}")


def example_6_auto_stop_loss():
    """Example 6: Auto Stop Loss - combining all exit strategies."""
    print("\n" + "="*60)
    print("Example 6: Auto Stop Loss (All Exits)")
    print("="*60)
    
    config = {
        'risk_management': {
            'stop_loss_percent': 1.0,
            'take_profit_percent': 2.0,
            'trailing_stop_percent': 0.5,
            'equity_target_percent': 5.0,
        }
    }
    
    manager = ExitStrategyManager(config)
    
    # Scenario 1: Signal change triggers exit
    print("\nScenario 1: Signal change (BUY→SELL)")
    result = manager.auto_stop_loss(
        entry_price=1.2500,
        current_price=1.2520,
        position_side="long",
        entry_signal="BUY",
        current_signal="SELL"
    )
    print(f"Should Exit: {result['should_exit']}")
    print(f"Primary Exit: {result['primary_exit']}")
    print(f"Action: {result['recommended_action']}")
    
    # Scenario 2: Stop loss has priority over signal change
    print("\nScenario 2: Stop loss priority (even with signal change)")
    result = manager.auto_stop_loss(
        entry_price=1.2500,
        current_price=1.2370,  # 1.04% loss
        position_side="long",
        entry_signal="BUY",
        current_signal="SELL"  # Signal also changed
    )
    print(f"Should Exit: {result['should_exit']}")
    print(f"Primary Exit: {result['primary_exit']} (stop loss has priority)")
    
    # Scenario 3: Multiple exits evaluated, none triggered
    print("\nScenario 3: No exit conditions met")
    result = manager.auto_stop_loss(
        entry_price=1.2500,
        current_price=1.2520,  # Small profit
        position_side="long",
        entry_signal="BUY",
        current_signal="BUY"  # No signal change
    )
    print(f"Should Exit: {result['should_exit']}")
    print(f"Action: {result['recommended_action']}")
    print(f"Exit checks performed: {len(result['exits'])}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("EXIT STRATEGY FRAMEWORK - USAGE EXAMPLES")
    print("="*60)
    
    example_1_direct_usage()
    example_2_trailing_stop()
    example_3_manager_usage()
    example_4_factory_pattern()
    example_5_signal_change_scenarios()
    example_6_auto_stop_loss()
    
    print("\n" + "="*60)
    print("Examples completed successfully!")
    print("="*60)
    print("\nFor more information, see: docs/EXIT_STRATEGIES.md")
