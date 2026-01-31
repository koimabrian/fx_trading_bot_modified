"""Core trading engine with improved position management.

REFACTORING NOTES:
- Integrated exit strategies from exit_strategies.py
- Multi-level position closing
- Improved trailing stops for profit protection
- Time-based exit for avoiding holding costs
"""

import logging
from datetime import datetime

import MetaTrader5 as mt5
import pandas as pd

from src.utils.exit_strategies import ExitStrategyManager
from src.utils.logging_factory import LoggingFactory


class TradeManager:
    """Manages open positions and exit strategy execution."""

    def __init__(self, mt5_connector, db, config=None):
        """Initialize trade manager.

        Args:
            mt5_connector: MT5 connector for order operations
            db: Database manager
            config: Configuration dict
        """
        self.mt5_connector = mt5_connector
        self.db = db
        self.config = config or {}
        self.exit_manager = ExitStrategyManager(config)
        self.logger = LoggingFactory.get_logger(__name__)
        self.position_tracking = {}  # Track entry_price, bars_held, etc.

    def track_position(self, position_id, entry_price, entry_bar=0):
        """Track an open position for exit monitoring.

        Args:
            position_id: Unique position identifier
            entry_price: Price where position was entered
            entry_bar: Bar number when position was opened
        """
        self.position_tracking[position_id] = {
            "entry_price": entry_price,
            "entry_bar": entry_bar,
            "current_bar": entry_bar,
            "max_price": entry_price,
            "min_price": entry_price,
        }

    def update_position(self, position_id, current_price, current_bar=None):
        """Update position tracking with latest price and bar.

        Args:
            position_id: Position identifier
            current_price: Current market price
            current_bar: Current bar number
        """
        if position_id not in self.position_tracking:
            return

        track = self.position_tracking[position_id]
        track["max_price"] = max(track["max_price"], current_price)
        track["min_price"] = min(track["min_price"], current_price)

        if current_bar is not None:
            track["current_bar"] = current_bar

    def evaluate_exit(self, position_id, data, current_price):
        """Evaluate if position should be exited based on multiple strategies.

        Args:
            position_id: Position identifier
            data: DataFrame with OHLC data
            current_price: Current market price

        Returns:
            Dict with exit evaluation results
        """
        if position_id not in self.position_tracking:
            return {"should_exit": False, "reason": "Position not tracked"}

        track = self.position_tracking[position_id]
        entry_price = track["entry_price"]
        bars_held = track["current_bar"] - track["entry_bar"]

        # Use combined exit strategy
        exit_eval = self.exit_manager.combined_exit_strategy(
            data=data,
            entry_price=entry_price,
            current_price=current_price,
            bars_held=bars_held,
            position_size=0.01,
        )

        return {
            "should_exit": exit_eval["recommended_action"] != "hold",
            "action": exit_eval["recommended_action"],
            "reason": exit_eval["primary_exit"],
            "details": exit_eval,
        }

    def get_position_profit(self, position_id, current_price):
        """Calculate current profit/loss for a position.

        Args:
            position_id: Position identifier
            current_price: Current market price

        Returns:
            Dict with profit metrics
        """
        if position_id not in self.position_tracking:
            return None

        track = self.position_tracking[position_id]
        entry_price = track["entry_price"]

        pnl = current_price - entry_price
        pnl_pct = (pnl / entry_price) * 100

        return {
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "is_profitable": pnl > 0,
            "bars_held": track["current_bar"] - track["entry_bar"],
            "max_profit": track["max_price"] - entry_price,
            "max_loss": track["min_price"] - entry_price,
        }

    def recommend_position_size(self, entry_price, stop_loss, account_risk_pct=2.0):
        """Calculate position size based on risk management.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            account_risk_pct: Percentage of account to risk (default 2%)

        Returns:
            Recommended position size (volume)
        """
        try:
            risk_per_pip = abs(entry_price - stop_loss)

            if risk_per_pip == 0:
                return 0.01  # Minimum default

            # Assuming 10000 account
            account_risk = 10000 * (account_risk_pct / 100)

            position_size = account_risk / risk_per_pip

            # Cap between 0.01 and 1.0
            return min(max(position_size, 0.01), 1.0)
        except Exception as e:
            self.logger.error("Position size calculation failed: %s", e)
            return 0.01

    def close_all_positions(self):
        """Close all open positions and release margin.

        Iterates through all open positions, closes each one using the MT5Connector,
        and provides a comprehensive summary of the closing operation.

        Returns:
            dict: Summary of the closing operation containing:
                - total_positions: Number of positions closed
                - successful_closes: Count of successful closures
                - failed_closes: Count of failed closures
                - closed_positions: List of successfully closed position details
                - failed_positions: List of failed position details with errors
                - account_status: Final account status after closing
        """
        try:
            # Retrieve all open positions
            positions = mt5.positions_get()

            if not positions:
                self.logger.info("No open positions to close")
                return {
                    "total_positions": 0,
                    "successful_closes": 0,
                    "failed_closes": 0,
                    "closed_positions": [],
                    "failed_positions": [],
                    "account_status": self._get_account_status(),
                }

            self.logger.info("Starting closure of %d open positions", len(positions))

            closed_positions = []
            failed_positions = []

            for pos in positions:
                try:
                    # Log position being closed
                    self.logger.debug(
                        "Closing position - Symbol: %s, Volume: %f, Type: %s, Ticket: %d",
                        pos.symbol,
                        pos.volume,
                        "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL",
                        pos.ticket,
                    )

                    # Use MT5Connector to close the position
                    success = self.mt5_connector.close_position(
                        position_id=pos.ticket,
                        symbol=pos.symbol,
                        position_type=pos.type,
                        volume=pos.volume,
                        comment="BULK_CLOSE_ALL_POSITIONS",
                    )

                    if success:
                        closed_positions.append(
                            {
                                "ticket": pos.ticket,
                                "symbol": pos.symbol,
                                "volume": pos.volume,
                                "type": (
                                    "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL"
                                ),
                            }
                        )
                        self.logger.info(
                            "Successfully closed position: %s (%f lots)",
                            pos.symbol,
                            pos.volume,
                        )
                    else:
                        failed_positions.append(
                            {
                                "ticket": pos.ticket,
                                "symbol": pos.symbol,
                                "volume": pos.volume,
                                "error": "MT5Connector close_position returned False",
                            }
                        )
                        self.logger.warning(
                            "Failed to close position: %s (%f lots)",
                            pos.symbol,
                            pos.volume,
                        )

                except Exception as e:
                    failed_positions.append(
                        {
                            "ticket": pos.ticket,
                            "symbol": pos.symbol,
                            "volume": pos.volume,
                            "error": str(e),
                        }
                    )
                    self.logger.error(
                        "Exception while closing position %s: %s", pos.symbol, e
                    )

            # Compile final summary
            summary = {
                "total_positions": len(positions),
                "successful_closes": len(closed_positions),
                "failed_closes": len(failed_positions),
                "closed_positions": closed_positions,
                "failed_positions": failed_positions,
                "account_status": self._get_account_status(),
            }

            self.logger.info(
                "Position closure complete: %d successful, %d failed",
                summary["successful_closes"],
                summary["failed_closes"],
            )

            return summary

        except Exception as e:
            self.logger.error("Critical error in close_all_positions: %s", e)
            return {
                "total_positions": 0,
                "successful_closes": 0,
                "failed_closes": 0,
                "closed_positions": [],
                "failed_positions": [{"error": str(e)}],
                "account_status": None,
            }

    def _get_account_status(self):
        """Get current account status.

        Returns:
            dict: Account status containing balance, equity, and open position count
        """
        try:
            account = mt5.account_info()
            if account:
                positions = mt5.positions_get()
                return {
                    "balance": account.balance,
                    "equity": account.equity,
                    "open_positions": len(positions) if positions else 0,
                    "trade_allowed": account.trade_allowed,
                }
            return None
        except Exception as e:
            self.logger.error("Failed to get account status: %s", e)
            return None
