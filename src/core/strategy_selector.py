# fx_trading_bot/src/core/strategy_selector.py
# Purpose: Ranks and selects best-performing strategies based on backtest results
import json
import logging
from typing import Dict, List

from src.utils.logging_factory import LoggingFactory


class StrategySelector:
    """Selects and ranks best-performing strategies based on backtest metrics."""

    def __init__(self, db):
        """Initialize StrategySelector with database connection.

        Args:
            db: Database manager instance
        """
        self.db = db
        self.logger = LoggingFactory.get_logger(__name__)
        self.strategy_cache = {}  # Cache loaded strategies

    def get_best_strategies(
        self,
        symbol: str,
        timeframe: str,
        top_n: int = 3,
        min_sharpe: float = 0.5,
    ) -> List[Dict]:
        """Get top-ranked strategies for a symbol/timeframe combination.

        Queries backtest_backtests table which contains metrics as JSON strings.
        Extracts metrics, computes rank_score, and returns top N strategies.

        Args:
            symbol: Trading symbol (e.g., 'BTCUSD')
            timeframe: Timeframe string (e.g., 'M15', 'H1')
            top_n: Number of top strategies to return (default 3)
            min_sharpe: Minimum Sharpe ratio threshold (default 0.5)

        Returns:
            List of strategy dicts sorted by rank_score (highest first)
        """
        cache_key = f"{symbol}_{timeframe}"

        # Check cache first
        if cache_key in self.strategy_cache:
            self.logger.debug(
                "Cache HIT: Best strategies for %s (%s)", symbol, timeframe
            )
            return self.strategy_cache[cache_key]

        try:
            # Query from backtest_backtests which stores metrics as JSON
            query = """
                SELECT DISTINCT
                    bs.name as strategy_name,
                    bb.metrics,
                    bb.timestamp
                FROM backtest_backtests bb
                JOIN backtest_strategies bs ON bb.strategy_id = bs.id
                JOIN tradable_pairs tp ON bb.symbol_id = tp.id
                WHERE tp.symbol = ? AND bb.timeframe = ?
                ORDER BY bb.timestamp DESC
            """

            results = self.db.execute_query(query, (symbol, timeframe))

            if not results:
                self.logger.warning(
                    "No backtest results found for %s (%s)",
                    symbol,
                    timeframe,
                )
                return []

            # Parse metrics JSON and filter by min_sharpe
            strategies = []
            for r in results:
                try:
                    metrics = (
                        json.loads(r["metrics"])
                        if isinstance(r["metrics"], str)
                        else r["metrics"]
                    )
                    sharpe = metrics.get("sharpe_ratio", 0)

                    if sharpe < min_sharpe:
                        continue

                    # Compute rank_score
                    rank_score = self.compute_rank_score(
                        sharpe_ratio=sharpe,
                        return_pct=metrics.get("total_return", 0),
                        win_rate_pct=metrics.get("win_rate", 50),
                        profit_factor=metrics.get("profit_factor", 1),
                    )

                    strategies.append(
                        {
                            "strategy_name": r["strategy_name"],
                            "sharpe_ratio": sharpe,
                            "return_pct": metrics.get("total_return", 0),
                            "win_rate_pct": metrics.get("win_rate", 50),
                            "profit_factor": metrics.get("profit_factor", 1),
                            "max_drawdown_pct": metrics.get("max_drawdown", 0),
                            "total_trades": metrics.get("total_trades", 0),
                            "winning_trades": metrics.get("winning_trades", 0),
                            "losing_trades": metrics.get("losing_trades", 0),
                            "sortino_ratio": metrics.get("sortino_ratio", 0),
                            "avg_win": metrics.get("avg_win", 0),
                            "avg_loss": metrics.get("avg_loss", 0),
                            "rank_score": rank_score,
                            "backtest_date": r["timestamp"],
                        }
                    )
                except (json.JSONDecodeError, TypeError, KeyError) as e:
                    self.logger.debug(
                        "Failed to parse metrics for %s (%s): %s",
                        symbol,
                        timeframe,
                        e,
                    )
                    continue

            # Sort by rank_score and take top N
            strategies.sort(key=lambda x: x["rank_score"], reverse=True)
            strategies = strategies[:top_n]

            if not strategies:
                self.logger.warning(
                    "No qualifying strategies (Sharpe >= %.2f) for %s (%s)",
                    min_sharpe,
                    symbol,
                    timeframe,
                )
                return []

            # Cache the results
            self.strategy_cache[cache_key] = strategies

            self.logger.debug(
                "Retrieved %d strategies for %s (%s): %s",
                len(strategies),
                symbol,
                timeframe,
                [s["strategy_name"] for s in strategies],
            )

            return strategies

        except (KeyError, ValueError, TypeError, RuntimeError) as e:
            self.logger.error(
                "Failed to get best strategies for %s (%s): %s", symbol, timeframe, e
            )
            return []

    def compute_rank_score(
        self,
        sharpe_ratio: float,
        return_pct: float,
        win_rate_pct: float,
        profit_factor: float,
    ) -> float:
        """Compute weighted rank score for strategy comparison.

        Weights:
        - Sharpe ratio (40%): Risk-adjusted returns
        - Return (30%): Total return percentage
        - Win rate (20%): Percentage of winning trades
        - Profit factor (10%): Profitability ratio

        Args:
            sharpe_ratio: Sharpe ratio (typically -2 to 5)
            return_pct: Return percentage (e.g., 5.5 for 5.5%)
            win_rate_pct: Win rate percentage (0-100)
            profit_factor: Profit factor (typically 1-3)

        Returns:
            Weighted rank score (0-100 scale)
        """
        # Normalize Sharpe (assume range -5 to 5, clip to 0-1)
        sharpe_norm = max(0, min(1, (sharpe_ratio + 5) / 10))

        # Normalize Return (assume range -20% to 100%, clip to 0-1)
        return_norm = max(0, min(1, (return_pct + 20) / 120))

        # Normalize Win Rate (already 0-100)
        win_rate_norm = win_rate_pct / 100

        # Normalize Profit Factor (assume typical range 0.5 to 3, clip to 0-1)
        pf_norm = max(0, min(1, (profit_factor - 0.5) / 2.5))

        # Compute weighted score
        score = (
            (sharpe_norm * 0.40)
            + (return_norm * 0.30)
            + (win_rate_norm * 0.20)
            + (pf_norm * 0.10)
        ) * 100

        return round(score, 2)

    def clear_cache(self) -> None:
        """Clear strategy cache."""
        self.strategy_cache.clear()
        self.logger.debug("Strategy cache cleared")

    def get_cache_size(self) -> int:
        """Get number of cached strategies."""
        return len(self.strategy_cache)
