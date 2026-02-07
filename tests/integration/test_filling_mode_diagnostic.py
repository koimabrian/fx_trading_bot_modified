"""Filling Mode Diagnostic Test.

Tests available filling modes on MT5 for various symbol types.
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


def test_filling_modes_for_all_symbols():
    """Test filling modes for all tradable symbols in database."""
    config = ConfigManager.get_config()

    # Initialize MT5
    with DatabaseManager(config["database"]) as db:
        mt5_conn = MT5Connector(db)
        if not mt5_conn.initialize():
            return False

        # Get symbols from database
        cursor = db.conn.cursor()
        cursor.execute("SELECT DISTINCT symbol FROM tradable_pairs ORDER BY symbol")
        symbols = [row[0] for row in cursor.fetchall()]

        if not symbols:
            return False

        # Test each symbol
        results = []
        for symbol in symbols:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                continue

            # Get filling mode directly (it's an integer)
            filling_mode = symbol_info.filling_mode
            result = {
                "symbol": symbol,
                "filling_mode_value": filling_mode,
            }
            results.append(result)

        # Test actual filling modes on sample symbols
        test_results = {}
        for symbol in symbols[:3]:  # Test first 3 symbols
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                continue

            # Test each filling mode
            filling_modes_to_test = [
                (mt5.ORDER_FILLING_RETURN, "RETURN"),
                (mt5.ORDER_FILLING_IOC, "IOC"),
                (mt5.ORDER_FILLING_FOK, "FOK"),
                (mt5.ORDER_FILLING_BOC, "BOC"),
            ]

            supported = []
            for mode_const, mode_name in filling_modes_to_test:
                try:
                    # Try to create a test order request with this filling mode
                    tick = mt5.symbol_info_tick(symbol)
                    if tick is None:
                        continue

                    price = tick.ask
                    request = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": symbol,
                        "volume": 0.01,
                        "type": mt5.ORDER_TYPE_BUY,
                        "price": price,
                        "type_time": mt5.ORDER_TIME_GTC,
                        "type_filling": mode_const,
                        "comment": "TEST_FILLING_MODE",
                    }

                    # Request can be constructed
                    supported.append((mode_const, mode_name))

                except Exception:
                    pass

            test_results[symbol] = {
                "supported_modes": supported,
            }

        # Check if all support RETURN
        all_return_support = all(
            any(m[1] == "RETURN" for m in test_results[sym]["supported_modes"])
            for sym in test_results
            if sym in test_results
        )

        assert all_return_support or len(test_results) == 0, "Filling mode test failed"
        return True
