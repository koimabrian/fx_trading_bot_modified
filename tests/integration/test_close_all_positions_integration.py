"""Test close_all_positions integration into TradeManager.

Verifies proper OOP design and no code redundancy.
"""

import sys
import os
import inspect

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.trade_manager import TradeManager
from src.core.mt5_connector import MT5Connector


def test_close_all_positions_integration():
    """Test that close_all_positions is properly integrated."""
    # 1. Verify method exists and is properly defined
    assert hasattr(TradeManager, "close_all_positions"), "Method not found!"

    # 2. Verify method signature
    method = getattr(TradeManager, "close_all_positions")
    sig = inspect.signature(method)
    params = list(sig.parameters.keys())
    assert params == ["self"], f"Unexpected parameters: {params}"

    # 3. Verify docstring exists and is complete
    doc = method.__doc__
    assert doc is not None, "No docstring found!"
    assert "Returns:" in doc, "No return documentation!"
    assert "dict" in doc, "Return type not documented!"

    # 4. Verify proper OOP integration
    source = inspect.getsource(method)
    assert "self.mt5_connector" in source, "Not using MT5Connector properly!"
    assert "self.logger" in source, "Not using logging!"

    # 5. Verify helper method exists
    assert hasattr(TradeManager, "_get_account_status"), "Helper method not found!"

    # 6. Verify no redundancy with MT5Connector
    mt5_source = inspect.getsource(MT5Connector.close_position)
    tm_source = inspect.getsource(TradeManager.close_all_positions)
    # The method should use close_position, not duplicate its logic
    assert (
        "self.mt5_connector.close_position" in tm_source
    ), "Method should use MT5Connector.close_position!"

    # 7. Verify error handling
    assert "try:" in source and "except" in source, "Missing error handling!"
    assert "failed_positions" in source, "Missing failure tracking!"

    # 8. Verify all methods are available
    methods = [m for m in dir(TradeManager) if not m.startswith("_")]
    required_methods = [
        "close_all_positions",
        "track_position",
        "update_position",
        "evaluate_exit",
        "get_position_profit",
        "recommend_position_size",
    ]
    for method_name in required_methods:
        assert method_name in methods, f"Missing method: {method_name}"
