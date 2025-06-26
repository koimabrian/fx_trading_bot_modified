# fx_trading_bot/src/strategy_manager.py
# Purpose: Manages dynamic loading and execution of rule-based trading strategies
import yaml
import logging
from typing import List, Dict, Any

class StrategyManager:
    def __init__(self, db):
        """Initialize strategy manager with config and database"""
        self.db = db
        self.strategies = []
        self.logger = logging.getLogger(__name__)
        self.load_config()

    def load_config(self) -> None:
        """Load strategy configurations from YAML and store in database"""
        try:
            with open('src/config/config.yaml', 'r') as file:
                config = yaml.safe_load(file)
            for strategy_config in config.get('strategies', []):
                strategy_name = strategy_config['name']
                params = strategy_config['params']
                # Dynamically import strategy classes
                if strategy_name == 'rsi':
                    from src.strategies.rsi_strategy import RSIStrategy
                    strategy = RSIStrategy(params, self.db)
                elif strategy_name == 'macd':
                    from src.strategies.macd_strategy import MACDStrategy
                    strategy = MACDStrategy(params, self.db)
                else:
                    self.logger.warning(f"Unknown strategy: {strategy_name}")
                    continue

                self.strategies.append(strategy)
                self.db.execute_query(
                    "INSERT OR REPLACE INTO strategies (name, parameters, filters, score, status, is_ml) VALUES (?, ?, ?, ?, ?, ?)",
                    (strategy_name, str(params), '{}', 0.0, 'live', False)
                )
            self.logger.debug(f"Loaded {len(self.strategies)} strategies")
        except Exception as e:
            self.logger.error(f"Failed to load strategy config: {e}")
            raise

    def generate_signals(self, strategy_name: str = None, symbol: str = None) -> List[Dict[str, Any]]:
        """Generate signals for the specified strategy or all strategies if none specified"""
        signals = []
        for strategy in self.strategies:
            if strategy_name and strategy.__class__.__name__.lower().startswith(strategy_name.lower()):
                # Pass the symbol to the strategy's generate_entry_signal method
                signal = strategy.generate_entry_signal(symbol=symbol)
                if signal:
                    signals.append(signal)
                    self.logger.debug(f"Generated signal from {strategy.__class__.__name__}: {signal}")
            elif not strategy_name:
                signal = strategy.generate_entry_signal(symbol=symbol)
                if signal:
                    signals.append(signal)
                    self.logger.debug(f"Generated signal from {strategy.__class__.__name__}: {signal}")
        return signals