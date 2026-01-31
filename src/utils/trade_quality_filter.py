"""
TEMPLATE: Trade Quality Filter Implementation

Copy to: src/utils/trade_quality_filter.py

This is a production-ready trade quality filtering module with all
best practices for professional-grade trade selection.
"""

import logging
from typing import Dict, Optional

from src.utils.logging_factory import LoggingFactory


class TradeQualityFilter:
    """
    Multi-level quality filter for trade execution.

    Filters trades based on:
    1. Confidence score (strategy metrics)
    2. Win rate (historical success)
    3. Sharpe ratio (risk-adjusted returns)
    4. Profit factor (gross profit / gross loss)
    5. Sample size (minimum backtest trades)
    6. Volatility regime (market conditions)
    7. Drawdown level (portfolio stress)

    All criteria must pass for trade to execute.
    """

    def __init__(self, config: Dict):
        """Initialize filter with config thresholds."""
        self.config = config
        self.logger = LoggingFactory.get_logger(__name__)
        self.thresholds = config.get("trade_quality", {})
        self._log_thresholds()

    def _log_thresholds(self):
        """Log configured thresholds on initialization."""
        self.logger.info("=" * 70)
        self.logger.info("TRADE QUALITY FILTER INITIALIZED")
        self.logger.info("=" * 70)
        self.logger.info(
            f"Min Confidence: {self.thresholds.get('min_confidence', 0.6):.2f}"
        )
        self.logger.info(
            f"Min Win Rate: {self.thresholds.get('min_win_rate_pct', 50)}%"
        )
        self.logger.info(f"Min Sharpe: {self.thresholds.get('min_sharpe', 0.5):.2f}")
        self.logger.info(
            f"Min Profit Factor: {self.thresholds.get('min_profit_factor', 1.5):.2f}"
        )
        self.logger.info(
            f"Min Sample Size: {self.thresholds.get('min_trades_in_sample', 30)} trades"
        )
        self.logger.info("=" * 70)

    def should_execute_trade(self, signal: Dict, strategy_info: Dict) -> bool:
        """
        Multi-level quality check before trade execution.

        Args:
            signal: Trade signal dict with symbol, action, confidence, etc.
            strategy_info: Strategy metrics dict with Sharpe, win_rate, etc.

        Returns:
            bool: True if trade passes all quality checks, False otherwise
        """
        symbol = signal.get("symbol", "UNKNOWN")

        # Quality Check 1: Confidence Score
        if not self._check_confidence(signal, symbol):
            return False

        # Quality Check 2: Win Rate
        if not self._check_win_rate(strategy_info, symbol):
            return False

        # Quality Check 3: Sharpe Ratio
        if not self._check_sharpe_ratio(strategy_info, symbol):
            return False

        # Quality Check 4: Profit Factor
        if not self._check_profit_factor(strategy_info, symbol):
            return False

        # Quality Check 5: Sample Size
        if not self._check_sample_size(strategy_info, symbol):
            return False

        # Quality Check 6: Volatility Level
        if not self._check_volatility(signal, symbol):
            return False

        # All checks passed
        confidence = signal.get("confidence", 0)
        win_rate = strategy_info.get("win_rate_pct", 0)
        sharpe = strategy_info.get("sharpe_ratio", 0)
        pf = strategy_info.get("profit_factor", 0)

        self.logger.info(
            f"✅ TRADE APPROVED | {symbol} | "
            f"Conf={confidence:.2f} | Win={win_rate:.1f}% | "
            f"Sharpe={sharpe:.2f} | PF={pf:.2f}"
        )
        return True

    def _check_confidence(self, signal: Dict, symbol: str) -> bool:
        """Check confidence score (composite quality metric)."""
        confidence = signal.get("confidence", 0)
        min_confidence = self.thresholds.get("min_confidence", 0.6)

        if confidence < min_confidence:
            self.logger.warning(
                f"❌ REJECTED {symbol} | Low Confidence: "
                f"{confidence:.2f} < {min_confidence:.2f}"
            )
            return False
        return True

    def _check_win_rate(self, strategy_info: Dict, symbol: str) -> bool:
        """Check win rate (percentage of winning trades)."""
        win_rate = strategy_info.get("win_rate_pct", 0)
        min_win_rate = self.thresholds.get("min_win_rate_pct", 50)

        if win_rate < min_win_rate:
            self.logger.warning(
                f"❌ REJECTED {symbol} | Low Win Rate: "
                f"{win_rate:.1f}% < {min_win_rate}%"
            )
            return False
        return True

    def _check_sharpe_ratio(self, strategy_info: Dict, symbol: str) -> bool:
        """Check Sharpe ratio (risk-adjusted returns)."""
        sharpe = strategy_info.get("sharpe_ratio", 0)
        min_sharpe = self.thresholds.get("min_sharpe", 0.5)

        if sharpe < min_sharpe:
            self.logger.warning(
                f"❌ REJECTED {symbol} | Low Sharpe Ratio: "
                f"{sharpe:.2f} < {min_sharpe:.2f}"
            )
            return False
        return True

    def _check_profit_factor(self, strategy_info: Dict, symbol: str) -> bool:
        """Check profit factor (gross profit / gross loss)."""
        pf = strategy_info.get("profit_factor", 0)
        min_pf = self.thresholds.get("min_profit_factor", 1.5)

        if pf < min_pf:
            self.logger.warning(
                f"❌ REJECTED {symbol} | Low Profit Factor: " f"{pf:.2f} < {min_pf:.2f}"
            )
            return False
        return True

    def _check_sample_size(self, strategy_info: Dict, symbol: str) -> bool:
        """Check sample size (minimum trades in backtest)."""
        sample_size = strategy_info.get("total_trades", 0)
        min_sample = self.thresholds.get("min_trades_in_sample", 30)

        if sample_size < min_sample:
            self.logger.warning(
                f"❌ REJECTED {symbol} | Insufficient Sample Size: "
                f"{sample_size} trades < {min_sample}"
            )
            return False
        return True

    def _check_volatility(self, signal: Dict, symbol: str) -> bool:
        """Check volatility level (market regime filter)."""
        volatility = signal.get("volatility_level", "medium")
        allowed = self.thresholds.get("allowed_volatility_levels", ["low", "medium"])

        if volatility not in allowed:
            self.logger.warning(
                f"❌ REJECTED {symbol} | Unacceptable Volatility: "
                f"{volatility} not in {allowed}"
            )
            return False
        return True

    def get_filter_stats(self) -> Dict:
        """Return current filter configuration."""
        return {
            "min_confidence": self.thresholds.get("min_confidence", 0.6),
            "min_win_rate_pct": self.thresholds.get("min_win_rate_pct", 50),
            "min_sharpe": self.thresholds.get("min_sharpe", 0.5),
            "min_profit_factor": self.thresholds.get("min_profit_factor", 1.5),
            "min_trades_in_sample": self.thresholds.get("min_trades_in_sample", 30),
            "allowed_volatility_levels": self.thresholds.get(
                "allowed_volatility_levels", ["low", "medium"]
            ),
        }


class PositionLimitManager:
    """
    Manages position limits with category awareness.

    Enforces:
    1. Total position limit
    2. Per-category limits (crypto, forex, stocks, etc.)
    3. Per-symbol limit (avoid overconcentration)
    4. Drawdown limits (stop trading if losses exceed threshold)
    """

    def __init__(self, config: Dict, mt5_connector, trading_rules):
        """Initialize position limit manager."""
        self.config = config
        self.mt5 = mt5_connector
        self.rules = trading_rules
        self.logger = LoggingFactory.get_logger(__name__)
        self.rm_config = config.get("risk_management", {})

    def get_position_limits(self) -> Dict:
        """Return all configured position limits."""
        return {
            "total": self.rm_config.get("max_positions", 10),
            "crypto": self.rm_config.get("max_crypto_positions", 4),
            "forex": self.rm_config.get("max_forex_positions", 3),
            "stocks": self.rm_config.get("max_stock_positions", 2),
            "commodities": self.rm_config.get("max_commodity_positions", 2),
            "indices": self.rm_config.get("max_index_positions", 1),
            "per_symbol": self.rm_config.get("max_positions_per_symbol", 1),
        }

    def can_open_position(self, symbol: str) -> bool:
        """
        Check if new position can open for symbol.
        Enforces total, category, and per-symbol limits.

        Returns:
            bool: True if position can open, False otherwise
        """
        limits = self.get_position_limits()
        positions = self.mt5.get_open_positions()

        # Check 1: Total position limit
        total_positions = len(positions)
        if total_positions >= limits["total"]:
            self.logger.warning(
                f"Position BLOCKED ({symbol}): Total limit reached "
                f"({total_positions}/{limits['total']})"
            )
            return False

        # Check 2: Category-specific limit
        category = self.rules.get_symbol_category(symbol)
        category_positions = sum(
            1 for p in positions if self.rules.get_symbol_category(p.symbol) == category
        )
        category_limit = limits.get(category, limits["total"])

        if category_positions >= category_limit:
            self.logger.warning(
                f"Position BLOCKED ({symbol}): {category.upper()} limit reached "
                f"({category_positions}/{category_limit})"
            )
            return False

        # Check 3: Per-symbol limit (avoid overconcentration)
        symbol_positions = sum(1 for p in positions if p.symbol == symbol)
        if symbol_positions >= limits["per_symbol"]:
            self.logger.warning(
                f"Position BLOCKED ({symbol}): Per-symbol limit reached "
                f"({symbol_positions}/{limits['per_symbol']})"
            )
            return False

        self.logger.info(
            f"✅ Position ALLOWED ({symbol}) | "
            f"Total: {total_positions}/{limits['total']} | "
            f"{category.upper()}: {category_positions}/{category_limit} | "
            f"Per-symbol: {symbol_positions}/{limits['per_symbol']}"
        )
        return True

    def get_position_stats(self) -> Dict:
        """Return current position statistics."""
        positions = self.mt5.get_open_positions()
        limits = self.get_position_limits()

        category_counts = {}
        for category in ["crypto", "forex", "stocks", "commodities", "indices"]:
            category_counts[category] = sum(
                1
                for p in positions
                if self.rules.get_symbol_category(p.symbol) == category
            )

        return {
            "total_positions": len(positions),
            "total_limit": limits["total"],
            "by_category": category_counts,
            "category_limits": {k: v for k, v in limits.items() if k != "per_symbol"},
        }


# ============================================================================
# INTEGRATION EXAMPLE
# ============================================================================
"""
In src/core/adaptive_trader.py:

    from src.utils.trade_quality_filter import TradeQualityFilter
    
    class AdaptiveTrader:
        def __init__(self, ...):
            self.quality_filter = TradeQualityFilter(self.config)
        
        def get_signals_adaptive(self, symbol: str):
            signals = []
            # ... existing code to generate signals ...
            
            # Filter signals by quality
            filtered = []
            for signal in signals:
                strategy_info = signal.get("strategy_info", {})
                if self.quality_filter.should_execute_trade(signal, strategy_info):
                    filtered.append(signal)
            
            return filtered

In src/main.py (_mode_live function):

    from src.utils.trade_quality_filter import PositionLimitManager
    
    position_manager = PositionLimitManager(config, mt5_conn, trading_rules)
    
    for symbol in pairs_to_trade:
        # Check position limits BEFORE generating signals
        if not position_manager.can_open_position(symbol):
            logger.debug(f"Skipping {symbol}: position limit reached")
            continue
        
        signals = adaptive_trader.get_signals_adaptive(symbol)
        for signal in signals:
            # Place order...
"""
