# fx_trading_bot/src/strategy_manager.py
# Purpose: Manages dynamic loading and execution of rule-based trading strategies
import yaml
import logging
from typing import List, Dict, Any
from src.strategies.factory import StrategyFactory

class StrategyManager:
    def __init__(self, db, mode='live'):
        """Initialize strategy manager with config and database"""
        self.db = db
        self.mode = mode
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
                try:
                    strategy = StrategyFactory.create_strategy(strategy_name, params, self.db, self.mode)
                    self.strategies.append(strategy)
                    self.db.execute_query(
                        "INSERT OR REPLACE INTO strategies (name, parameters, filters, score, status, is_ml) VALUES (?, ?, ?, ?, ?, ?)",
                        (strategy_name, str(params), '{}', 0.0, self.mode, False)
                    )
                except Exception as e:
                    self.logger.error(f"Failed to load strategy {strategy_name}: {e}")
            self.logger.debug(f"Loaded {len(self.strategies)} strategies")
        except Exception as e:
            self.logger.error(f"Failed to load strategy config: {e}")
            raise

    def generate_signals(self, strategy_name: str = None, symbol: str = None) -> List[Dict[str, Any]]:
        """Generate signals for the specified strategy or all strategies if none specified"""
        signals = []
        for strategy in self.strategies:
            if strategy_name and strategy.__class__.__name__.lower().startswith(strategy_name.lower()):
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