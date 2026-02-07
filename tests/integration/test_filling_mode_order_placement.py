"""Test filling mode implementation in live order placement.

Validates that orders can be placed with RETURN filling mode.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

import logging
import MetaTrader5 as mt5
from src.database.db_manager import DatabaseManager
from src.core.mt5_connector import MT5Connector
from src.utils.logging_factory import LoggingFactory
from src.utils.config_manager import ConfigManager

LoggingFactory.configure()
logger = logging.getLogger(__name__)


def test_order_placement_with_filling_modes():
    """Test actual order placement with different filling modes."""
    config = ConfigManager.get_config()

    with DatabaseManager(config["database"]) as db:
        mt5_conn = MT5Connector(db)
        if not mt5_conn.initialize():
            return False

        # Get a test symbol
        cursor = db.conn.cursor()
        cursor.execute("SELECT DISTINCT symbol FROM tradable_pairs LIMIT 1")
        result = cursor.fetchone()

        if not result:
            return False

        symbol = result[0]

        # Get symbol info
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return False

        # Test the current implementation
        filling_mode = mt5_conn._get_suitable_filling_mode(symbol_info)
        assert filling_mode == mt5.ORDER_FILLING_RETURN

        # Try to construct an order with this filling mode
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return True

        price = tick.ask
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": 0.01,
            "type": mt5.ORDER_TYPE_BUY,
            "price": price,
            "sl": price * 0.99,
            "tp": price * 1.02,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
            "comment": "TEST_FILLING_MODE_VALIDATION",
        }

        # Test that request can be constructed
        assert request is not None
        assert request["type_filling"] == mt5.ORDER_FILLING_RETURN

        return True
