# src/strategies/factory.py
from src.strategies.ema_strategy import EMAStrategy
from src.strategies.macd_strategy import MACDStrategy
from src.strategies.rsi_strategy import RSIStrategy
from src.strategies.sma_strategy import SMAStrategy


class StrategyFactory:
    """Factory class for creating strategy instances based on strategy name and mode."""

    @staticmethod
    def create_strategy(strategy_name, params, db, mode="live", config=None):
        """Create a strategy instance based on name and mode."""
        strategy_map = {
            "rsi": RSIStrategy,
            "macd": MACDStrategy,
            "sma": SMAStrategy,
            "ema": EMAStrategy,
        }
        strategy_class = strategy_map.get(strategy_name.lower())
        if not strategy_class:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        # Pass config if provided, otherwise pass empty dict
        return strategy_class(params, db, config or {}, mode=mode)
