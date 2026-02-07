# src/backtesting/trade_logger.py
# Purpose: Log detailed trade data during backtesting
import logging
from datetime import datetime
from typing import Dict, List

import pandas as pd

from src.utils.logging_factory import LoggingFactory


class TradeLogger:
    """Log and track detailed trade information during backtest."""

    def __init__(self):
        """Initialize trade logger."""
        self.logger = LoggingFactory.get_logger(__name__)
        self.trades: List[Dict] = []

    def log_trade(
        self,
        entry_time: datetime,
        exit_time: datetime,
        symbol: str,
        entry_price: float,
        exit_price: float,
        volume: float,
        profit: float,
    ) -> None:
        """Log a completed trade.

        Args:
            entry_time: Entry datetime
            exit_time: Exit datetime
            symbol: Trading symbol
            entry_price: Entry price
            exit_price: Exit price
            volume: Trade volume/size
            profit: Profit amount
        """
        profit_pct = ((exit_price - entry_price) / entry_price) * 100

        trade = {
            "entry_time": entry_time,
            "exit_time": exit_time,
            "symbol": symbol,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "volume": volume,
            "profit": profit,
            "profit_pct": profit_pct,
            "duration_hours": (exit_time - entry_time).total_seconds() / 3600,
        }

        self.trades.append(trade)
        self.logger.debug(
            "Logged trade: %s, profit: %.2f (%.2f%%)", symbol, profit, profit_pct
        )

    def get_trades(self) -> List[Dict]:
        """Get all logged trades.

        Returns:
            List of trade dictionaries
        """
        return self.trades

    def get_trades_df(self) -> pd.DataFrame:
        """Get all trades as pandas DataFrame.

        Returns:
            DataFrame with all trades
        """
        if not self.trades:
            return pd.DataFrame()

        return pd.DataFrame(self.trades)

    def get_trade_count(self) -> int:
        """Get total number of trades logged.

        Returns:
            Integer trade count
        """
        return len(self.trades)

    def get_winning_trades(self) -> List[Dict]:
        """Get all winning trades.

        Returns:
            List of winning trades
        """
        return [t for t in self.trades if t["profit"] > 0]

    def get_losing_trades(self) -> List[Dict]:
        """Get all losing trades.

        Returns:
            List of losing trades
        """
        return [t for t in self.trades if t["profit"] < 0]

    def clear(self) -> None:
        """Clear all logged trades.

        Returns:
            None.
        """
        self.trades = []
        self.logger.debug("Cleared all trades")

    def export_to_csv(self, filepath: str) -> bool:
        """Export trades to CSV file.

        Args:
            filepath: Path to export CSV file

        Returns:
            True if successful, False otherwise
        """
        try:
            df = self.get_trades_df()
            if df.empty:
                self.logger.warning("No trades to export")
                return False

            df.to_csv(filepath, index=False)
            self.logger.info("Exported %d trades to %s", len(df), filepath)
            return True
        except (IOError, OSError) as e:
            self.logger.error("Failed to export trades to CSV: %s", e)
            return False

    def get_summary(self) -> Dict:
        """Get summary statistics of all trades.

        Returns:
            Dictionary with summary statistics
        """
        if not self.trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_profit": 0.0,
                "avg_profit": 0.0,
                "avg_loss": 0.0,
            }

        winning = self.get_winning_trades()
        losing = self.get_losing_trades()

        total_profit = sum(t["profit"] for t in self.trades)
        avg_profit = (
            sum(t["profit"] for t in winning) / len(winning) if winning else 0.0
        )
        avg_loss = sum(t["profit"] for t in losing) / len(losing) if losing else 0.0

        return {
            "total_trades": len(self.trades),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": (len(winning) / len(self.trades)) * 100,
            "total_profit": total_profit,
            "avg_profit": avg_profit,
            "avg_loss": avg_loss,
        }
