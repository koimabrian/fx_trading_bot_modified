"""Adaptive trading engine with intelligent strategy selection.

Queries historical backtest results to automatically select and execute
the best-performing strategies for each symbol/timeframe combination.
Includes confidence scoring and strategy caching for optimization.
"""

import logging
from typing import List, Dict, Optional

from src.core.strategy_selector import StrategySelector
from src.strategies.factory import StrategyFactory
from src.utils.trading_rules import TradingRules
import yaml


class AdaptiveTrader:
    """Executes trades by automatically selecting best strategies from backtest results."""

    def __init__(self, strategy_manager, mt5_connector, db):
        """Initialize AdaptiveTrader.

        Args:
            strategy_manager: StrategyManager instance for strategy creation
            mt5_connector: MT5Connector instance for order placement
            db: Database manager instance
        """
        self.strategy_manager = strategy_manager
        self.mt5_connector = mt5_connector
        self.db = db
        self.logger = logging.getLogger(__name__)
        self.strategy_selector = StrategySelector(db)
        self.trading_rules = TradingRules()
        self.loaded_strategies = {}  # Cache for loaded strategy instances
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open("src/config/config.yaml", "r", encoding="utf-8") as file:
                return yaml.safe_load(file)
        except (FileNotFoundError, yaml.YAMLError, IOError, UnicodeDecodeError) as e:
            self.logger.error("Failed to load config: %s", e)
            return {}

    def _get_strategy_instance(
        self, strategy_name: str, symbol: str, timeframe: str
    ) -> Optional:
        """Load or retrieve cached strategy instance.

        Args:
            strategy_name: Name of strategy (e.g., 'rsi', 'macd')
            symbol: Trading symbol
            timeframe: Timeframe string

        Returns:
            Loaded strategy instance or None if fails
        """
        cache_key = f"{strategy_name}_{symbol}_{timeframe}"

        if cache_key in self.loaded_strategies:
            self.logger.debug("Strategy cache HIT: %s", cache_key)
            return self.loaded_strategies[cache_key]

        try:
            # Find strategy params from config
            strategy_config = next(
                (
                    s
                    for s in self.config.get("strategies", [])
                    if s["name"].lower() == strategy_name.lower()
                ),
                None,
            )

            if not strategy_config:
                self.logger.error("Strategy %s not found in config", strategy_name)
                return None

            # Create strategy instance
            strategy = StrategyFactory.create_strategy(
                strategy_name, strategy_config["params"], self.db, mode="live"
            )

            # Cache the strategy
            self.loaded_strategies[cache_key] = strategy
            self.logger.debug("Loaded and cached strategy: %s", cache_key)
            return strategy

        except (ValueError, KeyError, TypeError, AttributeError) as e:
            self.logger.error("Failed to load strategy %s: %s", strategy_name, e)
            return None

    def _compute_confidence(self, strategy_info: Dict) -> float:
        """Compute confidence score for a strategy based on its metrics.

        Confidence = (Sharpe + 5) / 10 * Win Rate / 100 * min(Profit Factor / 3, 1)

        Args:
            strategy_info: Dict with strategy metrics from DB

        Returns:
            Confidence score (0.0 to 1.0)
        """
        sharpe = strategy_info.get("sharpe_ratio", 0)
        win_rate = strategy_info.get("win_rate_pct", 50)
        profit_factor = strategy_info.get("profit_factor", 1)

        # Normalize and combine metrics
        sharpe_factor = max(0, (sharpe + 5) / 10)  # -5 to 5 range
        win_rate_factor = win_rate / 100  # 0 to 1
        pf_factor = min(profit_factor / 3, 1)  # normalized to 0-1

        confidence = sharpe_factor * win_rate_factor * pf_factor
        return min(max(confidence, 0), 1)  # Clamp to 0-1

    def get_signals_adaptive(self, symbol: str) -> List[Dict]:
        """Generate signals by selecting best strategies automatically.

        Queries database for top 3 strategies per symbol/timeframe,
        loads strategy instances, and generates signals without
        requiring user to specify which strategy to use.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSD')

        Returns:
            List of signals from best-performing strategies
        """
        signals = []

        try:
            # Get timeframes - try pairs list first, then pair_config
            pair_timeframes = [
                p["timeframe"]
                for p in self.config.get("pairs", [])
                if p["symbol"] == symbol
            ]

            if not pair_timeframes:
                # Fallback to pair_config timeframes if pairs list not populated
                pair_timeframes = self.config.get("pair_config", {}).get(
                    "timeframes", [15, 60, 240]
                )

            if not pair_timeframes:
                self.logger.warning("No timeframes configured for symbol %s", symbol)
                return []

            # Process each timeframe
            for tf in pair_timeframes:
                # Convert timeframe to string format (M15, H1, etc.)
                tf_str = f"M{tf}" if tf < 60 else f"H{tf // 60}"

                # Get best strategies for this symbol/timeframe from DB
                strategies = self.strategy_selector.get_best_strategies(
                    symbol=symbol,
                    timeframe=tf_str,
                    top_n=3,  # Use top 3 strategies
                    min_sharpe=0.5,
                )

                if not strategies:
                    self.logger.debug(
                        "No qualifying strategies for %s (%s)", symbol, tf_str
                    )
                    continue

                # Generate signals from best strategies
                for strategy_info in strategies:
                    strategy_name = strategy_info["strategy_name"]

                    # Load strategy instance
                    strategy = self._get_strategy_instance(
                        strategy_name, symbol, tf_str
                    )

                    if not strategy:
                        continue

                    # Generate entry signal
                    signal = strategy.generate_entry_signal(symbol=symbol)

                    if signal:
                        # Add confidence and strategy info
                        signal["confidence"] = self._compute_confidence(strategy_info)
                        signal["strategy_info"] = {
                            "name": strategy_name,
                            "sharpe": strategy_info["sharpe_ratio"],
                            "return_pct": strategy_info["return_pct"],
                            "win_rate": strategy_info["win_rate_pct"],
                            "rank_score": strategy_info["rank_score"],
                        }

                        signals.append(signal)

                        self.logger.debug(
                            "Generated adaptive signal for %s (%s) from %s: "
                            "confidence=%.2f, action=%s",
                            symbol,
                            tf_str,
                            strategy_name,
                            signal["confidence"],
                            signal.get("action"),
                        )

            return signals

        except (KeyError, ValueError, TypeError, AttributeError, RuntimeError) as e:
            self.logger.error("Error generating adaptive signals for %s: %s", symbol, e)
            return []

    def execute_adaptive_trades(self, symbol: Optional[str] = None) -> None:
        """Execute trades using adaptive strategy selection.

        Args:
            symbol: Optional specific symbol to trade. If None, trades all configured symbols.

        Iterates through configured symbols, generates adaptive signals,
        validates trading rules, and executes orders without requiring
        user-specified strategy.
        """
        try:
            # Get all unique symbols from config
            all_symbols = list(
                dict.fromkeys([p["symbol"] for p in self.config.get("pairs", [])])
            )

            # Use specified symbol or all configured symbols
            symbols = [symbol] if symbol else all_symbols

            for symbol in symbols:
                # Check if market is open
                self.trading_rules.log_trading_status(symbol)
                if not self.trading_rules.can_trade(symbol):
                    self.logger.debug(
                        "Market closed for %s (weekend/non-trading hours)", symbol
                    )
                    continue

                # Check position limits
                if not self._can_open_position():
                    self.logger.debug("Position limit reached")
                    break

                # Generate adaptive signals for this symbol
                signals = self.get_signals_adaptive(symbol)

                # Execute signals
                for signal in signals:
                    try:
                        self.logger.info(
                            "Executing adaptive trade for %s: %s (confidence=%.2f, "
                            "strategy=%s, sharpe=%.2f)",
                            signal["symbol"],
                            signal["action"],
                            signal.get("confidence", 0),
                            signal.get("strategy_info", {}).get("name", "unknown"),
                            signal.get("strategy_info", {}).get("sharpe", 0),
                        )

                        if self.mt5_connector.place_order(
                            signal,
                            f"{signal.get('strategy_info', {}).get('name', 'adaptive')}",
                        ):
                            self.logger.info(
                                "Adaptive trade executed for %s", signal["symbol"]
                            )
                        else:
                            self.logger.error(
                                "Failed to execute adaptive trade for %s",
                                signal["symbol"],
                            )

                    except (KeyError, ValueError, TypeError, RuntimeError) as e:
                        self.logger.error(
                            "Error executing signal for %s: %s", signal["symbol"], e
                        )

        except (KeyError, ValueError, TypeError, RuntimeError, AttributeError) as e:
            self.logger.error("Error executing adaptive trades: %s", e)

    def _can_open_position(self) -> bool:
        """Check if a new position can be opened based on position limits.

        Returns:
            Boolean indicating if position opening is allowed
        """
        current_positions = self.mt5_connector.get_open_positions_count()
        max_positions = self.config.get("risk_management", {}).get(
            "max_open_positions", 10
        )

        if current_positions >= max_positions:
            self.logger.warning(
                "Position limit reached: %d/%d open positions",
                current_positions,
                max_positions,
            )
            return False

        return True

    def clear_cache(self) -> None:
        """Clear all internal caches."""
        self.loaded_strategies.clear()
        self.strategy_selector.clear_cache()
        self.logger.debug("Adaptive trader caches cleared")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics for monitoring.

        Returns:
            Dictionary with cache stats
        """
        return {
            "loaded_strategies": len(self.loaded_strategies),
            "selector_cache": self.strategy_selector.get_cache_size(),
        }
