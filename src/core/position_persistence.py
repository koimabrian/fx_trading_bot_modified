"""
Position Persistence & Recovery Module

Handles:
1. Fetching existing open positions from MT5
2. Storing them in the trades table for recovery after restart
3. Monitoring positions across live trading sessions
4. Calculating position limits dynamically
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import MetaTrader5 as mt5

from src.utils.config_manager import ConfigManager
from src.utils.logging_factory import LoggingFactory


class PositionPersistence:
    """Manages position persistence across trading sessions."""

    def __init__(self, mt5_connector, db_manager, config: Dict = None):
        """Initialize position persistence manager.

        Args:
            mt5_connector: MT5Connector instance
            db_manager: DatabaseManager instance
            config: Configuration dictionary
        """
        self.mt5 = mt5_connector
        self.db = db_manager
        self.config = config or {}
        self.logger = LoggingFactory.get_logger(__name__)

    def fetch_and_store_mt5_positions(self, session_id: str = None) -> int:
        """Fetch all open positions from MT5 and store in trades table.

        This is called at startup to recover any positions opened before restart.

        Args:
            session_id: Optional session identifier for grouping

        Returns:
            Number of positions stored
        """
        try:
            # Get all open positions from MT5
            positions = mt5.positions_get()

            if not positions:
                self.logger.info("No open positions found in MT5")
                return 0

            positions_stored = 0
            session_id = session_id or datetime.now().isoformat()

            for position in positions:
                try:
                    # Store each position in trades table
                    result = self._store_position_in_trades_table(
                        position=position, session_id=session_id, status="OPEN"
                    )
                    if result:
                        positions_stored += 1
                        self.logger.info(
                            f"Stored position: {position.symbol} ticket={position.ticket} "
                            f"type={'BUY' if position.type == 0 else 'SELL'} "
                            f"volume={position.volume} entry={position.price_open}"
                        )
                except Exception as e:
                    self.logger.warning(f"Failed to store position: {e}")
                    continue

            self.logger.info(
                f"Stored {positions_stored}/{len(positions)} positions in trades table"
            )
            return positions_stored

        except Exception as e:
            self.logger.error(f"Failed to fetch MT5 positions: {e}")
            return 0

    def _store_position_in_trades_table(
        self, position, session_id: str, status: str = "OPEN"
    ) -> bool:
        """Store a single position in the trades table.

        Args:
            position: MT5 position object
            session_id: Session identifier
            status: Position status (OPEN, MONITORING, etc.)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract position details
            symbol = position.symbol
            ticket = position.ticket
            trade_type = "BUY" if position.type == 0 else "SELL"
            volume = position.volume
            entry_price = position.price_open
            entry_time = datetime.fromtimestamp(position.time)
            current_price = position.price_current
            profit_loss = position.profit
            swap = position.swap
            commission = position.commission

            # SQL to insert position into trades table
            query = """
            INSERT INTO trades (
                ticket, symbol, trade_type, volume, entry_price, entry_time,
                current_price, profit_loss, swap, commission, status, session_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            params = (
                ticket,
                symbol,
                trade_type,
                volume,
                entry_price,
                entry_time,
                current_price,
                profit_loss,
                swap,
                commission,
                status,
                session_id,
                datetime.now(),
            )

            self.db.conn.execute(query, params)
            self.db.conn.commit()

            return True

        except Exception as e:
            self.logger.error(f"Failed to store position: {e}")
            return False

    def get_open_positions_by_symbol(self, symbol: str) -> List[Dict]:
        """Get all open positions for a specific symbol from trades table.

        Args:
            symbol: Trading symbol (e.g., 'EURUSD')

        Returns:
            List of position dictionaries
        """
        try:
            query = """
            SELECT * FROM trades
            WHERE symbol = ? AND status IN ('OPEN', 'MONITORING')
            ORDER BY entry_time ASC
            """

            cursor = self.db.conn.execute(query, (symbol,))
            positions = [dict(row) for row in cursor.fetchall()]

            return positions

        except Exception as e:
            self.logger.error(f"Failed to get positions by symbol: {e}")
            return []

    def get_position_count_by_category(self, category: str) -> Tuple[int, int]:
        """Get open position count and limit for a category.

        Args:
            category: Asset category (FOREX, CRYPTO, STOCKS, etc.)

        Returns:
            Tuple of (current_count, limit)
        """
        try:
            # Category limits from config (with fallback defaults)
            config = ConfigManager.get_config()

            # Get limits from config or use defaults
            config_limits = config.get("risk_management", {}).get("category_limits", {})
            category_limits = {
                "forex": config_limits.get("forex", 3),
                "crypto": config_limits.get("crypto", 4),
                "stocks": config_limits.get("stocks", 2),
                "commodities": config_limits.get("commodities", 2),
                "indices": config_limits.get("indices", 1),
            }

            limit = category_limits.get(category.lower(), 15)

            # Query positions table for this category
            # This requires a symbol_category mapping (should be in database)
            query = """
            SELECT COUNT(*) as count FROM trades
            WHERE status IN ('OPEN', 'MONITORING')
            AND symbol IN (
                SELECT symbol FROM tradable_pairs WHERE category = ?
            )
            """

            cursor = self.db.conn.execute(query, (category.lower(),))
            result = cursor.fetchone()
            current_count = result[0] if result else 0

            return current_count, limit

        except Exception as e:
            self.logger.error(f"Failed to get category position count: {e}")
            return 0, 5

    def get_total_position_count(self) -> Tuple[int, int]:
        """Get total open positions and limit.

        Returns:
            Tuple of (current_count, limit)
        """
        try:
            limit = self.config.get("risk_management", {}).get("max_positions", 15)

            query = """
            SELECT COUNT(*) as count FROM trades
            WHERE status IN ('OPEN', 'MONITORING')
            """

            cursor = self.db.conn.execute(query)
            result = cursor.fetchone()
            current_count = result[0] if result else 0

            return current_count, limit

        except Exception as e:
            self.logger.error(f"Failed to get total position count: {e}")
            return 0, 5

    def update_position_monitoring(
        self, ticket: int, current_price: float, profit_loss: float = None
    ) -> bool:
        """Update position during monitoring (price/profit updates).

        Args:
            ticket: Position ticket number
            current_price: Current market price
            profit_loss: Current profit/loss (optional)

        Returns:
            True if successful
        """
        try:
            query = """
            UPDATE trades
            SET current_price = ?, profit_loss = ?, updated_at = ?
            WHERE ticket = ?
            """

            params = (current_price, profit_loss, datetime.now(), ticket)

            self.db.conn.execute(query, params)
            self.db.conn.commit()

            return True

        except Exception as e:
            self.logger.error(f"Failed to update position monitoring: {e}")
            return False

    def close_position_record(self, ticket: int, exit_price: float) -> bool:
        """Mark a position as closed in the trades table.

        Args:
            ticket: Position ticket number
            exit_price: Price at which position was closed

        Returns:
            True if successful
        """
        try:
            query = """
            UPDATE trades
            SET status = 'CLOSED', exit_price = ?, closed_at = ?
            WHERE ticket = ?
            """

            params = (exit_price, datetime.now(), ticket)

            self.db.conn.execute(query, params)
            self.db.conn.commit()

            self.logger.info(f"Closed position record: ticket={ticket}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to close position record: {e}")
            return False

    def can_open_position(self, symbol: str, category: str) -> Tuple[bool, str]:
        """Check if a new position can be opened based on stored positions.

        Checks:
        1. Total position limit (5)
        2. Category limit (FOREX: 3, CRYPTO: 4, etc.)
        3. Per-symbol limit (5)

        Args:
            symbol: Trading symbol
            category: Asset category

        Returns:
            Tuple of (can_open: bool, reason: str)
        """
        # Check 1: Total position limit
        total_count, total_limit = self.get_total_position_count()
        if total_count >= total_limit:
            return False, f"Total limit reached ({total_count}/{total_limit})"

        # Check 2: Category limit
        category_count, category_limit = self.get_position_count_by_category(category)
        if category_count >= category_limit:
            return (
                False,
                f"{category.upper()} limit reached ({category_count}/{category_limit})",
            )

        # Check 3: Per-symbol limit
        symbol_positions = self.get_open_positions_by_symbol(symbol)
        per_symbol_limit = self.config.get("risk_management", {}).get(
            "max_positions_per_symbol", 5
        )
        if len(symbol_positions) >= per_symbol_limit:
            return (
                False,
                f"Per-symbol limit reached ({len(symbol_positions)}/{per_symbol_limit})",
            )

        return True, "OK"

    def clear_trades_table_for_fresh_session(self) -> int:
        """Clear closed trades from trades table for a fresh session.

        Only removes CLOSED positions, keeps OPEN positions for recovery.

        Returns:
            Number of records deleted
        """
        try:
            query = "DELETE FROM trades WHERE status = 'CLOSED'"

            cursor = self.db.conn.execute(query)
            self.db.conn.commit()
            deleted_count = cursor.rowcount

            self.logger.info(f"Cleared {deleted_count} closed trades for fresh session")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Failed to clear trades table: {e}")
            return 0

    def get_session_summary(self) -> Dict:
        """Get summary of current trading session.

        Returns:
            Dictionary with session statistics
        """
        try:
            # Total positions
            total_count, total_limit = self.get_total_position_count()

            # Category breakdown
            categories = ["forex", "crypto", "stocks", "commodities", "indices"]
            category_breakdown = {}
            for cat in categories:
                count, limit = self.get_position_count_by_category(cat)
                category_breakdown[cat] = {"count": count, "limit": limit}

            # Profit/loss summary
            query = """
            SELECT
                COUNT(*) as total_trades,
                SUM(profit_loss) as total_pnl,
                AVG(profit_loss) as avg_pnl,
                MAX(profit_loss) as max_profit,
                MIN(profit_loss) as max_loss
            FROM trades
            WHERE status IN ('OPEN', 'CLOSED')
            """

            cursor = self.db.conn.execute(query)
            result = dict(cursor.fetchone())

            return {
                "total_positions": total_count,
                "total_limit": total_limit,
                "positions_available": total_limit - total_count,
                "by_category": category_breakdown,
                "performance": {
                    "total_trades": result.get("total_trades", 0),
                    "total_pnl": result.get("total_pnl", 0),
                    "avg_pnl": result.get("avg_pnl", 0),
                    "max_profit": result.get("max_profit", 0),
                    "max_loss": result.get("max_loss", 0),
                },
            }

        except Exception as e:
            self.logger.error(f"Failed to get session summary: {e}")
            return {}

    def close_all_positions_emergency(self) -> int:
        """Close ALL open positions immediately (emergency risk limit enforcement).

        Returns:
            Number of positions closed
        """
        try:
            positions_closed = 0

            # Get all open positions
            query = """
                SELECT id, symbol_id FROM trades 
                WHERE status IN ('OPEN', 'MONITORING')
            """

            cursor = self.db.conn.execute(query)
            open_positions = cursor.fetchall()

            # Close each position
            for position in open_positions:
                try:
                    pos_id = position[0]
                    # Mark as closed at current time
                    close_query = """
                        UPDATE trades 
                        SET status = 'CLOSED', close_time = ?
                        WHERE id = ?
                    """

                    self.db.conn.execute(close_query, [datetime.now(), pos_id])
                    self.db.conn.commit()

                    positions_closed += 1
                    self.logger.warning(f"Emergency closed position ID: {pos_id}")

                except Exception as e:
                    self.logger.error(f"Failed to emergency close position: {e}")
                    continue

            self.logger.critical(
                f"Emergency: Closed {positions_closed} positions due to daily loss limit"
            )
            return positions_closed

        except Exception as e:
            self.logger.error(f"Failed in emergency position close: {e}")
            return 0
