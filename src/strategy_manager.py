# src/strategy_manager.py
import yaml
import logging
from typing import List, Dict, Any
from src.core.factory import StrategyFactory

class StrategyManager:
    """Manages dynamic loading and execution of trading strategies."""
    def __init__(self, db, config, mode='live'):
        self.db = db
        self.config = config
        self.mode = mode
        self.strategies = []
        self.logger = logging.getLogger(__name__)
        self.table_prefix = 'backtest_' if mode == 'backtest' else ''
        self.load_strategies()

    def load_strategies(self):
        """Load strategy configurations from YAML and store in database."""
        try:
            with open('src/config/config.yaml', 'r') as file:
                config = yaml.safe_load(file)
            strategies_table = f"{self.table_prefix}strategies"
            # Ensure strategies table exists
            self.db.execute_query(
                f"""
                CREATE TABLE IF NOT EXISTS {strategies_table} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    parameters TEXT,
                    filters TEXT,
                    score REAL,
                    status TEXT,
                    is_ml BOOLEAN
                )
                """
            )
            for strategy_config in config.get('strategies', []):
                strategy_name = strategy_config['name']
                params = strategy_config['params']
                strategy = StrategyFactory.create_strategy(strategy_name, params, self.db, self.config, mode=self.mode)
                self.strategies.append(strategy)
                self.db.execute_query(
                    f"INSERT OR REPLACE INTO {strategies_table} (name, parameters, filters, score, status, is_ml) VALUES (?, ?, ?, ?, ?, ?)",
                    (strategy_name, str(params), '{}', 0.0, self.mode, strategy_name in ['random_forest', 'lstm'])
                )
            self.logger.debug(f"Loaded {len(self.strategies)} strategies in {self.mode} mode")
        except Exception as e:
            self.logger.error(f"Failed to load strategy config: {e}")
            raise

    def generate_signals(self, strategy_name: str = None, symbol: str = None) -> List[Dict[str, Any]]:
        """Generate signals for the specified strategy or all strategies."""
        signals = []
        for strategy in self.strategies:
            if strategy_name and strategy.__class__.__name__.lower().startswith(strategy_name.lower()):
                signal = strategy.generate_entry_signal(symbol=symbol)
                if signal:
                    signals.append(signal)
                    self.logger.debug(f"Generated signal from {strategy.__class__.__name__} in {self.mode} mode: {signal}")
            elif not strategy_name:
                signal = strategy.generate_entry_signal(symbol=symbol)
                if signal:
                    signals.append(signal)
                    self.logger.debug(f"Generated signal from {strategy.__class__.__name__} in {self.mode} mode: {signal}")
        return signals