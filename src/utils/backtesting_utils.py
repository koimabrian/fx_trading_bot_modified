"""Backtesting utilities for volatility analysis and strategy selection.

Provides functions for ATR-based volatility ranking, parameter selection,
and adaptive strategy choosing for live trading.
"""

import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd


def calculate_atr(data: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range (ATR) for volatility measurement.

    Args:
        data: DataFrame with 'high', 'low', 'close' columns
        period: ATR period (default 14)

    Returns:
        Series of ATR values
    """
    logger = logging.getLogger(__name__)

    try:
        # Calculate True Range
        high_low = data["high"] - data["low"]
        high_close = abs(data["high"] - data["close"].shift())
        low_close = abs(data["low"] - data["close"].shift())

        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)

        # Calculate ATR
        atr = true_range.rolling(window=period).mean()

        logger.debug(
            f"Calculated ATR (period={period}): min={atr.min():.6f}, max={atr.max():.6f}, mean={atr.mean():.6f}"
        )
        return atr
    except (KeyError, ValueError) as e:
        logger.error(f"Error calculating ATR: {e}")
        return pd.Series(dtype=float)


def volatility_rank_pairs(
    db_conn,
    tradable_pairs: List[str],
    timeframe: str,
    atr_period: int = 14,
    lookback_bars: int = 200,
    min_threshold: float = 0.001,
    top_n: int = 10,
) -> Dict[str, float]:
    """Rank trading pairs by volatility (ATR) and select top N.

    Implements workflow Step B: Volatility Ranking for live trading.

    Args:
        db_conn: SQLite database connection
        tradable_pairs: List of symbol names (e.g., ['EURUSD', 'GBPUSD'])
        timeframe: Timeframe string (e.g., 'H1', 'H4')
        atr_period: ATR calculation period
        lookback_bars: Number of recent bars to use for ranking
        min_threshold: Minimum ATR to consider (skips low-vol pairs)
        top_n: Number of top pairs to select

    Returns:
        Dict {symbol: atr_value} for top N pairs, ordered by ATR (descending)

    Example:
        >>> ranked = volatility_rank_pairs(
        ...     db_conn,
        ...     ['EURUSD', 'GBPUSD', 'USDJPY'],
        ...     'H1',
        ...     top_n=10
        ... )
        >>> # Returns: {'EURUSD': 0.0125, 'GBPUSD': 0.0110, ...}
    """
    logger = logging.getLogger(__name__)
    ranked_pairs = {}
    skipped_pairs = []

    try:
        for symbol in tradable_pairs:
            try:
                # Handle both DatabaseManager and sqlite3 connection
                if hasattr(db_conn, "conn"):
                    # db_conn is a DatabaseManager object
                    connection = db_conn.conn
                else:
                    # db_conn is a sqlite3 connection
                    connection = db_conn

                # Fetch recent market data using direct symbol (v2 schema)
                query = """
                    SELECT open, high, low, close
                    FROM market_data
                    WHERE symbol = ? AND timeframe = ?
                    ORDER BY time DESC
                    LIMIT ?
                """
                data = pd.read_sql_query(
                    query, connection, params=(symbol, timeframe, lookback_bars)
                )

                if data is None or len(data) < atr_period:
                    logger.debug(
                        f"{symbol}: Insufficient data ({len(data) if data is not None else 0} rows) "
                        f"for ATR calculation (need {atr_period})"
                    )
                    skipped_pairs.append((symbol, "insufficient_data"))
                    continue

                # Reverse to chronological order (oldest first)
                data = data.iloc[::-1].reset_index(drop=True)

                # Calculate ATR
                atr_series = calculate_atr(data, period=atr_period)
                current_atr = atr_series.iloc[-1]  # Latest ATR value

                # Filter by minimum threshold
                if pd.isna(current_atr) or current_atr < min_threshold:
                    logger.debug(
                        f"{symbol}: ATR {current_atr:.6f} below threshold {min_threshold:.6f}"
                    )
                    skipped_pairs.append((symbol, f"low_vol_{current_atr:.6f}"))
                    continue

                ranked_pairs[symbol] = float(current_atr)
                logger.debug(f"{symbol} ({timeframe}): ATR = {current_atr:.6f}")

            except (pd.errors.DatabaseError, KeyError, ValueError) as e:
                logger.warning(f"Error calculating ATR for {symbol}: {e}")
                skipped_pairs.append((symbol, str(e)))
                continue

        # Sort by ATR descending and select top N
        sorted_pairs = sorted(ranked_pairs.items(), key=lambda x: x[1], reverse=True)
        top_pairs = dict(sorted_pairs[:top_n])

        logger.info(
            f"Volatility Ranking ({timeframe}): Selected {len(top_pairs)}/{len(tradable_pairs)} pairs. "
            f"Skipped {len(skipped_pairs)}: {skipped_pairs[:3]}"
        )

        return top_pairs

    except Exception as e:
        logger.error(f"Fatal error in volatility_rank_pairs: {e}")
        return {}


def get_strategy_parameters_from_optimal(
    db_conn,
    symbol: str,
    timeframe: str,
) -> Optional[Tuple[str, Dict]]:
    """Fetch optimal parameters for a symbol/timeframe from optimal_parameters table.

    Implements workflow Step C Priority 1: Query optimal_parameters.

    Args:
        db_conn: SQLite database connection
        symbol: Trading symbol (e.g., 'EURUSD')
        timeframe: Timeframe (e.g., 'H1')

    Returns:
        Tuple of (strategy_name, parameters_dict) or None if not found
    """
    logger = logging.getLogger(__name__)

    try:
        # Query optimal parameters using FK join (symbol_id -> tradable_pairs)
        query = """
            SELECT op.strategy_name, op.parameter_value
            FROM optimal_parameters op
            INNER JOIN tradable_pairs tp ON op.symbol_id = tp.id
            WHERE tp.symbol = ? AND op.timeframe = ?
            ORDER BY op.last_optimized DESC
            LIMIT 1
        """
        result = pd.read_sql_query(query, db_conn, params=(symbol, timeframe))

        if result is None or len(result) == 0:
            logger.debug(f"No optimal parameters found for {symbol} ({timeframe})")
            return None

        strategy_name = result.iloc[0]["strategy_name"]
        # parameter_value is stored as JSON string, parse it
        import json

        params = json.loads(result.iloc[0]["parameter_value"])

        logger.debug(
            f"Found optimal params for {symbol} ({timeframe}): {strategy_name}"
        )
        return (strategy_name, params)

    except (pd.errors.DatabaseError, KeyError, ValueError, json.JSONDecodeError) as e:
        logger.error(f"Error fetching optimal parameters for {symbol}/{timeframe}: {e}")
        return None


def query_top_strategies_by_rank_score(
    db_conn,
    symbol: str,
    timeframe: str,
    top_n: int = 3,
) -> List[Tuple[str, Dict, float]]:
    """Query backtest_backtests for top N strategies by rank_score (fallback).

    Implements workflow Step C Fallback: Query backtest_backtests.
    Returns top performers to use when optimal_parameters unavailable.

    Args:
        db_conn: SQLite database connection
        symbol: Trading symbol
        timeframe: Timeframe
        top_n: Number of top strategies to return

    Returns:
        List of tuples: [(strategy_name, metrics_dict, rank_score), ...]
    """
    logger = logging.getLogger(__name__)

    try:
        cursor = db_conn.cursor()

        query = """
            SELECT bb.strategy_id, bb.metrics, bs.name as strategy_name
            FROM backtest_backtests bb
            LEFT JOIN backtest_strategies bs ON bb.strategy_id = bs.id
            INNER JOIN tradable_pairs tp ON bb.symbol_id = tp.id
            WHERE tp.symbol = ? AND bb.timeframe = ?
            ORDER BY json_extract(bb.metrics, '$.rank_score') DESC
            LIMIT ?
        """
        results = pd.read_sql_query(query, db_conn, params=(symbol, timeframe, top_n))

        if results is None or len(results) == 0:
            logger.debug(f"No backtest results found for {symbol} ({timeframe})")
            return []

        strategies = []
        import json

        for _, row in results.iterrows():
            strategy_name = row.get("strategy_name", f"strategy_{row['strategy_id']}")
            metrics = (
                json.loads(row["metrics"])
                if isinstance(row["metrics"], str)
                else row["metrics"]
            )
            rank_score = float(metrics.get("rank_score", 0))

            strategies.append((strategy_name, metrics, rank_score))
            logger.debug(f"Found strategy {strategy_name}: rank_score={rank_score:.4f}")

        logger.info(
            f"Found {len(strategies)} top strategies for {symbol} ({timeframe})"
        )
        return strategies

    except (pd.errors.DatabaseError, KeyError, ValueError, json.JSONDecodeError) as e:
        logger.error(
            f"Error querying backtest strategies for {symbol}/{timeframe}: {e}"
        )
        return []


def extract_strategy_params_from_metrics(metrics: Dict) -> Dict:
    """Extract strategy parameters from metrics JSON stored in backtest_backtests.

    Maps metrics back to strategy parameters for execution.

    Args:
        metrics: Metrics dictionary from backtest_backtests

    Returns:
        Dictionary of strategy parameters
    """
    logger = logging.getLogger(__name__)

    # Map metric keys to strategy parameter keys
    # This depends on strategy type - customize as needed
    param_mapping = {
        "period": "period",
        "overbought": "overbought",
        "oversold": "oversold",
        "fast_period": "fast_period",
        "slow_period": "slow_period",
        "signal_period": "signal_period",
    }

    params = {}
    for metric_key, param_key in param_mapping.items():
        if metric_key in metrics:
            params[param_key] = metrics[metric_key]

    if not params:
        logger.warning(f"No parameters extracted from metrics: {metrics}")

    return params
