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
from src.utils.backtesting_utils import (
    volatility_rank_pairs,
    get_strategy_parameters_from_optimal,
    query_top_strategies_by_rank_score,
)
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

        IMPROVED: More lenient scoring to allow more trades
        - Positive Sharpe: 0.6-1.0 confidence
        - Neutral Sharpe (0-1): 0.5-0.6 confidence
        - Negative Sharpe: still trade if profit factor > 1.2 (0.4-0.5)

        Args:
            strategy_info: Dict with strategy metrics from DB

        Returns:
            Confidence score (0.0 to 1.0)
        """
        sharpe = strategy_info.get("sharpe_ratio", 0)
        win_rate = strategy_info.get("win_rate_pct", 50)
        profit_factor = strategy_info.get("profit_factor", 1.0)

        # Base confidence from Sharpe ratio
        if sharpe > 1.0:
            base_confidence = 0.8  # Strong strategy
        elif sharpe > 0.5:
            base_confidence = 0.7  # Good strategy
        elif sharpe > 0:
            base_confidence = 0.6  # Acceptable strategy
        elif profit_factor > 1.2:
            base_confidence = 0.5  # Marginal but tradeable
        else:
            base_confidence = 0.3  # Only trade if other factors strong

        # Adjust for win rate
        win_rate_factor = min(win_rate / 100, 1.0)

        # Adjust for profit factor (normalize 1.0-3.0 range)
        pf_factor = min(profit_factor / 2.0, 1.0)

        # Combined confidence
        confidence = base_confidence * (0.5 + 0.3 * win_rate_factor + 0.2 * pf_factor)

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
            # Check trading rules (weekend, market hours, etc.)
            if not self.trading_rules.can_trade(symbol):
                self.logger.warning(
                    "Trading disabled for %s - market closed (weekend or non-trading hours)",
                    symbol,
                )
                return []

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
                    min_sharpe=-0.5,  # Allow negative Sharpe if profit factor good (IMPROVED)
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

    def run_pre_signal_checks(
        self, active_symbols: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, Optional[tuple]]]:
        """Execute Pre-Signal Checks (Step A-D of live workflow).

        Implements strict order:
          Step A: Load active pairs
          Step B: Volatility ranking - select top N by ATR
          Step C: Parameter selection - optimal → fallback to backtest results
          Step D: Cache strategies

        Args:
            active_symbols: List of symbols to check. If None, load all from tradable_pairs.

        Returns:
            Dict mapping {symbol: {timeframe: (strategy_name, parameters)}}
        """
        logger = self.logger
        selected_pairs = {}

        try:
            # Step A: Load active pairs from tradable_pairs table
            if active_symbols:
                active_pairs = active_symbols
                logger.info(f"Step A: Using specified symbols: {active_symbols}")
            else:
                # Load from tradable_pairs table
                query = "SELECT DISTINCT symbol FROM tradable_pairs"
                result = self.db.execute_query(query)
                active_pairs = [row["symbol"] for row in result] if result else []
                logger.info(
                    f"Step A: Loaded {len(active_pairs)} active pairs from database"
                )

            if not active_pairs:
                logger.warning("No active pairs found in tradable_pairs table")
                return {}

            # Get timeframes from config
            timeframes = self.config.get("timeframes", [60, 240, 1440])

            # Step B: Volatility Ranking
            volatility_config = self.config.get("volatility", {})
            atr_period = volatility_config.get("atr_period", 14)
            lookback_bars = volatility_config.get("lookback_bars", 200)
            min_threshold = volatility_config.get("min_threshold", 0.001)
            top_n_pairs = volatility_config.get("top_n_pairs", 10)

            for timeframe in timeframes:
                tf_str = f"M{timeframe}" if timeframe < 60 else f"H{timeframe // 60}"

                logger.info(f"Step B: Volatility Ranking for {tf_str}...")
                ranked_pairs = volatility_rank_pairs(
                    self.db.conn,
                    active_pairs,
                    tf_str,
                    atr_period=atr_period,
                    lookback_bars=lookback_bars,
                    min_threshold=min_threshold,
                    top_n=top_n_pairs,
                )

                if not ranked_pairs:
                    logger.warning(f"No pairs passed volatility filter for {tf_str}")
                    continue

                logger.info(
                    f"Step B: {tf_str} - Selected {len(ranked_pairs)} pairs by volatility. "
                    f"Top 3: {list(ranked_pairs.items())[:3]}"
                )

                # Step C & D: Parameter selection and strategy caching
                for symbol in ranked_pairs.keys():
                    logger.debug(
                        f"Step C-D: Selecting parameters for {symbol} ({tf_str})..."
                    )

                    # Priority 1: Query optimal_parameters
                    optimal = get_strategy_parameters_from_optimal(
                        self.db.conn, symbol, tf_str
                    )

                    if optimal:
                        strategy_name, params = optimal
                        logger.info(
                            f"  Priority 1 (Optimal): {symbol} ({tf_str}) → {strategy_name}"
                        )
                        # Cache strategy
                        strategy = self._get_strategy_instance(
                            strategy_name, symbol, tf_str
                        )
                        if strategy:
                            if symbol not in selected_pairs:
                                selected_pairs[symbol] = {}
                            selected_pairs[symbol][tf_str] = (strategy_name, params)
                    else:
                        # Fallback: Query backtest_backtests by rank_score
                        fallback = query_top_strategies_by_rank_score(
                            self.db.conn, symbol, tf_str, top_n=1
                        )

                        if fallback:
                            strategy_name, metrics, rank_score = fallback[0]
                            logger.info(
                                f"  Fallback (Adaptive): {symbol} ({tf_str}) → {strategy_name} "
                                f"(rank={rank_score:.4f})"
                            )
                            # Extract params from metrics
                            from src.utils.backtesting_utils import (
                                extract_strategy_params_from_metrics,
                            )

                            params = extract_strategy_params_from_metrics(metrics)

                            # Cache strategy
                            strategy = self._get_strategy_instance(
                                strategy_name, symbol, tf_str
                            )
                            if strategy:
                                if symbol not in selected_pairs:
                                    selected_pairs[symbol] = {}
                                selected_pairs[symbol][tf_str] = (strategy_name, params)
                        else:
                            logger.warning(
                                f"  No strategy found for {symbol} ({tf_str}). Skipping."
                            )

            logger.info(
                f"Step D: Cached strategies. Total pairs selected: {len(selected_pairs)}"
            )
            return selected_pairs

        except Exception as e:
            logger.error(f"Error in pre-signal checks: {e}")
            return {}

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
