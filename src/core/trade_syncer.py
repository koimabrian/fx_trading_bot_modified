"""Synchronize historical trades from MT5 to database.

This module provides functionality to sync completed deals, order history,
and open positions from MetaTrader5 to the local database. This ensures
external trades placed via MT5 terminal are captured and trade history
is complete.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import MetaTrader5 as mt5

from src.utils.logging_factory import LoggingFactory
from src.utils.mt5_decorator import mt5_safe


class TradeSyncer:
    """Synchronizes historical trades from MT5 to database.
    
    This class handles:
    1. Syncing completed deals from MT5 history
    2. Syncing order history
    3. Syncing currently open positions
    4. Reconciling database state with MT5 reality
    """

    def __init__(self, db, mt5_connector):
        """Initialize TradeSyncer.
        
        Args:
            db: DatabaseManager instance for database operations
            mt5_connector: MT5Connector instance for MT5 operations
        """
        self.db = db
        self.mt5 = mt5_connector
        self.logger = LoggingFactory.get_logger(__name__)

    @mt5_safe(max_retries=3)
    def sync_deals_from_mt5(self, days_back: int = 30) -> int:
        """Sync completed deals from MT5 history.
        
        Uses mt5.history_deals_get() to retrieve historical deals and
        stores them in the database. This captures trades closed via
        MT5 terminal or other external means.
        
        Args:
            days_back: How many days of history to sync (default: 30)
            
        Returns:
            Number of deals successfully synced to database
        """
        try:
            from_date = datetime.now() - timedelta(days=days_back)
            to_date = datetime.now()
            
            self.logger.info(
                "Fetching deals from MT5 history (%s to %s)...",
                from_date.date(),
                to_date.date()
            )
            
            deals = mt5.history_deals_get(from_date, to_date)
            if deals is None or len(deals) == 0:
                self.logger.warning("No deals returned from MT5 history")
                return 0
            
            self.logger.info("Retrieved %d deals from MT5", len(deals))
            
            synced = 0
            for deal in deals:
                if self._upsert_deal(deal):
                    synced += 1
            
            self.logger.info(
                "Synced %d/%d deals from MT5 to database",
                synced,
                len(deals)
            )
            return synced
            
        except Exception as e:
            self.logger.error("Failed to sync deals from MT5: %s", e)
            return 0

    @mt5_safe(max_retries=3)
    def sync_orders_from_mt5(self, days_back: int = 30) -> int:
        """Sync order history from MT5.
        
        Uses mt5.history_orders_get() to retrieve historical orders and
        stores them in the database. This provides complete order audit trail.
        
        Args:
            days_back: How many days of history to sync (default: 30)
            
        Returns:
            Number of orders successfully synced to database
        """
        try:
            from_date = datetime.now() - timedelta(days=days_back)
            to_date = datetime.now()
            
            self.logger.info(
                "Fetching orders from MT5 history (%s to %s)...",
                from_date.date(),
                to_date.date()
            )
            
            orders = mt5.history_orders_get(from_date, to_date)
            if orders is None or len(orders) == 0:
                self.logger.warning("No orders returned from MT5 history")
                return 0
            
            self.logger.info("Retrieved %d orders from MT5", len(orders))
            
            synced = 0
            for order in orders:
                if self._upsert_order(order):
                    synced += 1
            
            self.logger.info(
                "Synced %d/%d orders from MT5 to database",
                synced,
                len(orders)
            )
            return synced
            
        except Exception as e:
            self.logger.error("Failed to sync orders from MT5: %s", e)
            return 0

    @mt5_safe(max_retries=3)
    def sync_open_positions(self) -> int:
        """Sync currently open positions from MT5.
        
        Uses mt5.positions_get() to retrieve current positions and
        ensures they are reflected in the database.
        
        Returns:
            Number of positions successfully synced
        """
        try:
            positions = mt5.positions_get()
            if positions is None or len(positions) == 0:
                self.logger.info("No open positions in MT5")
                return 0
            
            self.logger.info("Retrieved %d open positions from MT5", len(positions))
            
            synced = 0
            for pos in positions:
                if self._upsert_position(pos):
                    synced += 1
            
            self.logger.info(
                "Synced %d/%d open positions to database",
                synced,
                len(positions)
            )
            return synced
            
        except Exception as e:
            self.logger.error("Failed to sync open positions from MT5: %s", e)
            return 0

    def reconcile_with_database(self) -> Dict:
        """Compare MT5 positions with database and reconcile.
        
        Identifies discrepancies between database state and MT5 reality:
        - Positions marked 'open' in DB but closed in MT5
        - Positions in MT5 but missing from DB
        
        Returns:
            Dict with reconciliation results containing:
            - closed_in_mt5: List of tickets closed in MT5 but marked open in DB
            - missing_in_db: List of tickets in MT5 but not in DB
            - synced: List of tickets successfully reconciled
        """
        try:
            # Get open positions from MT5
            mt5_positions_raw = mt5.positions_get()
            if mt5_positions_raw is None:
                mt5_positions_raw = []
            
            mt5_positions = {p.ticket: p for p in mt5_positions_raw}
            
            # Get 'open' trades from database
            db_open_query = """
                SELECT order_id, deal_id, status, id
                FROM trades
                WHERE status = 'open'
            """
            db_open = self.db.execute_query(db_open_query).fetchall()
            
            results = {
                "closed_in_mt5": [],      # DB says open, MT5 says closed
                "missing_in_db": [],      # MT5 has position, DB doesn't
                "synced": [],             # Successfully reconciled
            }
            
            # Check DB positions against MT5
            for row in db_open:
                # Try order_id first, fallback to deal_id
                ticket = row["order_id"] if row["order_id"] else row["deal_id"]
                
                if ticket and ticket not in mt5_positions:
                    results["closed_in_mt5"].append(ticket)
                    # Update DB to reflect closed status
                    self._mark_trade_closed(row["id"])
            
            # Check for MT5 positions not in DB
            db_tickets = {
                (row["order_id"] if row["order_id"] else row["deal_id"])
                for row in db_open
            }
            
            for ticket in mt5_positions.keys():
                if ticket not in db_tickets:
                    results["missing_in_db"].append(ticket)
                    # Sync this position to DB
                    if self._upsert_position(mt5_positions[ticket]):
                        results["synced"].append(ticket)
            
            self.logger.info(
                "Reconciliation complete: %d closed in MT5, %d missing in DB, %d synced",
                len(results["closed_in_mt5"]),
                len(results["missing_in_db"]),
                len(results["synced"])
            )
            
            return results
            
        except Exception as e:
            self.logger.error("Failed to reconcile with database: %s", e)
            return {"closed_in_mt5": [], "missing_in_db": [], "synced": []}

    def _upsert_deal(self, deal) -> bool:
        """Insert or update a deal in the database.
        
        Args:
            deal: MT5 deal object from history_deals_get()
            
        Returns:
            True if successfully stored, False otherwise
        """
        try:
            # Get symbol_id from tradable_pairs
            symbol_query = "SELECT id FROM tradable_pairs WHERE symbol = ?"
            symbol_result = self.db.execute_query(
                symbol_query,
                (deal.symbol,)
            ).fetchone()
            
            if not symbol_result:
                self.logger.debug(
                    "Symbol %s not in tradable_pairs, skipping deal %d",
                    deal.symbol,
                    deal.ticket
                )
                return False
            
            symbol_id = symbol_result["id"]
            
            # Determine trade type (BUY or SELL)
            # deal.type: 0=buy, 1=sell
            trade_type = "BUY" if deal.type == 0 else "SELL"
            
            # Insert or update deal in trades table
            upsert_query = """
                INSERT INTO trades (
                    symbol_id, timeframe, strategy_name, trade_type,
                    volume, open_price, close_price, open_time, close_time,
                    profit, status, order_id, deal_id, ticket, magic,
                    swap, commission, comment, external, mt5_synced_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(deal_id) DO UPDATE SET
                    close_price = excluded.close_price,
                    close_time = excluded.close_time,
                    profit = excluded.profit,
                    status = excluded.status,
                    mt5_synced_at = excluded.mt5_synced_at
            """
            
            # MT5 deal times are in seconds since epoch
            open_time = datetime.fromtimestamp(deal.time).isoformat()
            close_time = datetime.fromtimestamp(deal.time).isoformat()
            
            # Note: MT5 deals only contain the execution price, not separate open/close
            # For accurate trade history, deals should be correlated with their
            # originating orders/positions. For now, we store deal.price for both.
            # This is a known limitation of the MT5 deals API.
            
            self.db.execute_query(
                upsert_query,
                (
                    symbol_id,
                    "UNKNOWN",  # timeframe not available in deal
                    "EXTERNAL",  # strategy name for external trades
                    trade_type,
                    deal.volume,
                    deal.price,
                    deal.price,  # For deals, open_price = close_price
                    open_time,
                    close_time,
                    deal.profit,
                    "closed",  # Deals are always closed
                    deal.order,
                    deal.ticket,
                    deal.ticket,
                    deal.magic,
                    deal.swap if hasattr(deal, 'swap') else 0,
                    deal.commission if hasattr(deal, 'commission') else 0,
                    deal.comment if hasattr(deal, 'comment') else "",
                    1,  # external = True
                    datetime.now().isoformat()
                )
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to upsert deal %d: %s", deal.ticket, e)
            return False

    def _upsert_order(self, order) -> bool:
        """Insert or update an order in the database.
        
        Args:
            order: MT5 order object from history_orders_get()
            
        Returns:
            True if successfully stored, False otherwise
        """
        try:
            # Get symbol_id from tradable_pairs
            symbol_query = "SELECT id FROM tradable_pairs WHERE symbol = ?"
            symbol_result = self.db.execute_query(
                symbol_query,
                (order.symbol,)
            ).fetchone()
            
            if not symbol_result:
                self.logger.debug(
                    "Symbol %s not in tradable_pairs, skipping order %d",
                    order.symbol,
                    order.ticket
                )
                return False
            
            symbol_id = symbol_result["id"]
            
            # Determine trade type
            # order.type: 0=buy, 1=sell, 2=buy_limit, 3=sell_limit, etc.
            trade_type = "BUY" if order.type in [0, 2, 4] else "SELL"
            
            # Determine order status
            # order.state: 0=started, 1=placed, 2=canceled, 3=partial, 4=filled, etc.
            status_map = {
                0: "started",
                1: "placed",
                2: "canceled",
                3: "partial",
                4: "filled",
                5: "rejected",
                6: "expired",
                7: "request_add",
                8: "request_modify",
                9: "request_cancel",
            }
            status = status_map.get(order.state, "unknown")
            
            # Insert or update order
            upsert_query = """
                INSERT INTO trades (
                    symbol_id, timeframe, strategy_name, trade_type,
                    volume, open_price, open_time, status, order_id,
                    ticket, magic, comment, external, mt5_synced_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_id) DO UPDATE SET
                    status = excluded.status,
                    mt5_synced_at = excluded.mt5_synced_at
            """
            
            # MT5 order times are in seconds since epoch
            open_time = datetime.fromtimestamp(order.time_setup).isoformat()
            
            self.db.execute_query(
                upsert_query,
                (
                    symbol_id,
                    "UNKNOWN",
                    "EXTERNAL",
                    trade_type,
                    order.volume_initial,
                    order.price_open if order.price_open > 0 else order.price_current,
                    open_time,
                    status,
                    order.ticket,
                    order.ticket,
                    order.magic,
                    order.comment if hasattr(order, 'comment') else "",
                    1,  # external = True
                    datetime.now().isoformat()
                )
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to upsert order %d: %s", order.ticket, e)
            return False

    def _upsert_position(self, position) -> bool:
        """Insert or update a position in the database.
        
        Args:
            position: MT5 position object from positions_get()
            
        Returns:
            True if successfully stored, False otherwise
        """
        try:
            # Get symbol_id from tradable_pairs
            symbol_query = "SELECT id FROM tradable_pairs WHERE symbol = ?"
            symbol_result = self.db.execute_query(
                symbol_query,
                (position.symbol,)
            ).fetchone()
            
            if not symbol_result:
                self.logger.debug(
                    "Symbol %s not in tradable_pairs, skipping position %d",
                    position.symbol,
                    position.ticket
                )
                return False
            
            symbol_id = symbol_result["id"]
            
            # Determine trade type
            trade_type = "BUY" if position.type == 0 else "SELL"
            
            # Calculate current profit
            profit = position.profit + position.swap + position.commission
            
            # Insert or update position
            upsert_query = """
                INSERT INTO trades (
                    symbol_id, timeframe, strategy_name, trade_type,
                    volume, open_price, close_price, open_time,
                    profit, status, order_id, deal_id, ticket, magic,
                    swap, commission, comment, external, mt5_synced_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ticket) DO UPDATE SET
                    close_price = excluded.close_price,
                    profit = excluded.profit,
                    swap = excluded.swap,
                    commission = excluded.commission,
                    mt5_synced_at = excluded.mt5_synced_at
            """
            
            # Position times are in seconds since epoch
            open_time = datetime.fromtimestamp(position.time).isoformat()
            
            self.db.execute_query(
                upsert_query,
                (
                    symbol_id,
                    "UNKNOWN",
                    "EXTERNAL",
                    trade_type,
                    position.volume,
                    position.price_open,
                    position.price_current,
                    open_time,
                    profit,
                    "open",
                    position.ticket,
                    position.ticket,
                    position.ticket,
                    position.magic,
                    position.swap,
                    position.commission,
                    position.comment,
                    1,  # external = True
                    datetime.now().isoformat()
                )
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to upsert position %d: %s", position.ticket, e)
            return False

    def _mark_trade_closed(self, trade_id: int) -> None:
        """Mark a trade as closed in the database.
        
        Args:
            trade_id: Database ID of the trade to mark as closed
        """
        try:
            update_query = """
                UPDATE trades
                SET status = 'closed', close_time = ?
                WHERE id = ? AND status = 'open'
            """
            self.db.execute_query(
                update_query,
                (datetime.now().isoformat(), trade_id)
            )
            self.logger.debug("Marked trade %d as closed", trade_id)
            
        except Exception as e:
            self.logger.error("Failed to mark trade %d as closed: %s", trade_id, e)
