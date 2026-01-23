# src/strategies/factory.py
from src.strategies.rsi_strategy import RSIStrategy
from src.strategies.macd_strategy import MACDStrategy


class StrategyFactory:
    """Factory class for creating strategy instances based on strategy name and mode."""

    @staticmethod
    def create_strategy(strategy_name, params, db, mode="live", config=None):
        """Create a strategy instance based on name and mode."""
        strategy_map = {"rsi": RSIStrategy, "macd": MACDStrategy}
        strategy_class = strategy_map.get(strategy_name.lower())
        if not strategy_class:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        # Pass config if provided, otherwise pass empty dict
        return strategy_class(params, db, config or {}, mode=mode)
