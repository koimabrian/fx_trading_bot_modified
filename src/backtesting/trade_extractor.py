"""
Trade Extractor - Extract and analyze individual trades from backtest.py results.

The backtesting.py library stores detailed trade information in the stats object
via the private _trades attribute. This module provides utilities to safely extract,
analyze, and store this trade data.
"""

import logging
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np


logger = logging.getLogger(__name__)


class TradeExtractor:
    """Extract detailed trade data from backtesting.py stats objects."""

    @staticmethod
    def extract_trades(stats: Any) -> pd.DataFrame:
        """Extract individual trades from backtest stats object.

        The backtesting.py Stats object stores trades in _trades attribute.
        Each trade contains entry/exit times, prices, size, and P&L.

        Args:
            stats: Stats object returned from backtesting.py Backtest.run()

        Returns:
            DataFrame with columns: entry_time, exit_time, entry_price,
                                    exit_price, size, pnl, pnl_pct, duration_hours
                    Empty DataFrame if no trades or extraction fails
        """
        try:
            # Access the private _trades attribute from stats object
            if not hasattr(stats, "_trades"):
                logger.warning("Stats object has no _trades attribute")
                return pd.DataFrame()

            trades_list = stats._trades
            if not trades_list or len(trades_list) == 0:
                logger.info("No trades found in backtest results")
                return pd.DataFrame()

            # Convert trades to DataFrame
            trades_data = []
            for trade in trades_list:
                try:
                    # Extract key trade information
                    trade_dict = {
                        "entry_time": trade.entry_time,
                        "exit_time": trade.exit_time,
                        "entry_price": trade.entry_price,
                        "exit_price": trade.exit_price,
                        "size": trade.size,
                        "pnl": trade.pl,  # Profit/Loss in currency
                        "pnl_pct": trade.plpct,  # Profit/Loss in percentage
                        "duration_hours": (
                            trade.exit_time - trade.entry_time
                        ).total_seconds()
                        / 3600,
                    }
                    trades_data.append(trade_dict)
                except (AttributeError, TypeError) as e:
                    logger.warning(f"Error extracting trade data: {e}")
                    continue

            if not trades_data:
                logger.warning("No valid trades could be extracted")
                return pd.DataFrame()

            df = pd.DataFrame(trades_data)
            logger.info(f"Extracted {len(df)} trades from backtest results")
            return df

        except Exception as e:
            logger.error(f"Error extracting trades from stats: {e}")
            return pd.DataFrame()

    @staticmethod
    def calculate_trade_statistics(trades_df: pd.DataFrame) -> Dict[str, float]:
        """Calculate comprehensive statistics from trades DataFrame.

        Args:
            trades_df: DataFrame returned from extract_trades()

        Returns:
            Dictionary with trade statistics:
                - total_trades: Total number of trades
                - winning_trades: Number of winning trades
                - losing_trades: Number of losing trades
                - win_rate: Win rate as percentage
                - avg_win: Average winning trade return (%)
                - avg_loss: Average losing trade return (%)
                - largest_win: Largest single win (%)
                - largest_loss: Largest single loss (%)
                - profit_factor: Total wins / Total losses
                - avg_duration_hours: Average trade duration
                - total_pnl: Total P&L
                - total_pnl_pct: Total return (%)
        """
        if trades_df is None or len(trades_df) == 0:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
                "profit_factor": 0.0,
                "avg_duration_hours": 0.0,
                "total_pnl": 0.0,
                "total_pnl_pct": 0.0,
            }

        try:
            winning = trades_df[trades_df["pnl"] > 0]
            losing = trades_df[trades_df["pnl"] < 0]

            total_wins = winning["pnl"].sum() if len(winning) > 0 else 0
            total_losses = abs(losing["pnl"].sum()) if len(losing) > 0 else 0

            stats = {
                "total_trades": len(trades_df),
                "winning_trades": len(winning),
                "losing_trades": len(losing),
                "win_rate": (
                    (len(winning) / len(trades_df) * 100) if len(trades_df) > 0 else 0
                ),
                "avg_win": winning["pnl_pct"].mean() if len(winning) > 0 else 0,
                "avg_loss": losing["pnl_pct"].mean() if len(losing) > 0 else 0,
                "largest_win": trades_df["pnl_pct"].max() if len(trades_df) > 0 else 0,
                "largest_loss": trades_df["pnl_pct"].min() if len(trades_df) > 0 else 0,
                "profit_factor": (total_wins / total_losses) if total_losses > 0 else 0,
                "avg_duration_hours": (
                    trades_df["duration_hours"].mean() if len(trades_df) > 0 else 0
                ),
                "total_pnl": trades_df["pnl"].sum(),
                "total_pnl_pct": trades_df["pnl_pct"].sum(),
            }

            logger.info(
                f"Trade statistics calculated: {stats['total_trades']} trades, "
                f"{stats['win_rate']:.1f}% win rate"
            )
            return stats

        except Exception as e:
            logger.error(f"Error calculating trade statistics: {e}")
            return {}

    @staticmethod
    def get_trades_by_timeframe(trades_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Group trades by hour-of-day to identify peak trading times.

        Args:
            trades_df: DataFrame returned from extract_trades()

        Returns:
            Dictionary with hour as key (0-23) and trade statistics as value
        """
        if trades_df is None or len(trades_df) == 0:
            return {}

        try:
            trades_df["hour"] = pd.to_datetime(trades_df["entry_time"]).dt.hour
            hourly_stats = {}

            for hour in range(24):
                hour_trades = trades_df[trades_df["hour"] == hour]
                if len(hour_trades) > 0:
                    winning = len(hour_trades[hour_trades["pnl"] > 0])
                    hourly_stats[str(hour)] = {
                        "count": len(hour_trades),
                        "win_count": winning,
                        "avg_pnl_pct": hour_trades["pnl_pct"].mean(),
                        "total_pnl": hour_trades["pnl"].sum(),
                    }

            logger.info(
                f"Calculated hourly trade distribution for {len(hourly_stats)} hours"
            )
            return hourly_stats

        except Exception as e:
            logger.error(f"Error calculating trades by timeframe: {e}")
            return {}

    @staticmethod
    def get_winning_losing_breakdown(trades_df: pd.DataFrame) -> Dict[str, Any]:
        """Get detailed breakdown of winning vs losing trades.

        Args:
            trades_df: DataFrame returned from extract_trades()

        Returns:
            Dictionary with winning/losing trade analysis
        """
        if trades_df is None or len(trades_df) == 0:
            return {
                "winning": [],
                "losing": [],
                "consecutive_wins_max": 0,
                "consecutive_losses_max": 0,
            }

        try:
            winning = trades_df[trades_df["pnl"] > 0].to_dict("records")
            losing = trades_df[trades_df["pnl"] < 0].to_dict("records")

            # Calculate consecutive wins/losses
            trades_df["is_win"] = trades_df["pnl"] > 0
            win_streaks = TradeExtractor._calculate_streaks(
                trades_df["is_win"].tolist()
            )
            max_consecutive_wins = max(win_streaks) if win_streaks else 0

            loss_streaks = TradeExtractor._calculate_streaks(
                (~trades_df["is_win"]).tolist()
            )
            max_consecutive_losses = max(loss_streaks) if loss_streaks else 0

            return {
                "winning": winning,
                "losing": losing,
                "consecutive_wins_max": max_consecutive_wins,
                "consecutive_losses_max": max_consecutive_losses,
            }

        except Exception as e:
            logger.error(f"Error calculating winning/losing breakdown: {e}")
            return {}

    @staticmethod
    def _calculate_streaks(is_win_list: List[bool]) -> List[int]:
        """Calculate consecutive win/loss streaks.

        Args:
            is_win_list: List of boolean values (True for win, False for loss)

        Returns:
            List of streak lengths
        """
        if not is_win_list:
            return []

        streaks = []
        current_streak = 1

        for i in range(1, len(is_win_list)):
            if is_win_list[i] == is_win_list[i - 1]:
                current_streak += 1
            else:
                streaks.append(current_streak)
                current_streak = 1

        streaks.append(current_streak)
        return streaks

    @staticmethod
    def export_trades_csv(trades_df: pd.DataFrame, filepath: str) -> bool:
        """Export trades to CSV file.

        Args:
            trades_df: DataFrame returned from extract_trades()
            filepath: Output filepath

        Returns:
            True if successful, False otherwise
        """
        try:
            if trades_df is None or len(trades_df) == 0:
                logger.warning("No trades to export")
                return False

            trades_df.to_csv(filepath, index=False)
            logger.info(f"Trades exported to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Error exporting trades to CSV: {e}")
            return False
