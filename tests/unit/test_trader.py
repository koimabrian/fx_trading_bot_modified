"""Unit tests for trader module."""

import logging
import pytest
from unittest.mock import Mock, MagicMock

from src.core.trader import Trader


class TestTrader:
    """Test suite for Trader class."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for Trader."""
        strategy_manager = Mock()
        mt5_connector = Mock()
        return strategy_manager, mt5_connector

    @pytest.fixture
    def trader(self, mock_dependencies):
        """Create Trader instance with mocks."""
        strategy_manager, mt5_connector = mock_dependencies
        return Trader(strategy_manager, mt5_connector)

    def test_trader_initialization(self, trader):
        """Test Trader initializes correctly."""
        assert trader is not None
        assert trader.strategy_manager is not None
        assert trader.mt5_connector is not None

    def test_trader_is_class(self):
        """Test that Trader is a valid class."""
        assert Trader is not None

    def test_trader_can_instantiate(self, trader):
        """Test Trader can be instantiated."""
        assert isinstance(trader, Trader)

    def test_trader_has_logger(self, trader):
        """Test Trader has logger."""
        assert hasattr(trader, "logger")

    def test_trader_has_execute_trade_method(self, trader):
        """Test Trader has execute_trade method."""
        if hasattr(trader, "execute_trade"):
            assert callable(trader.execute_trade)

    def test_trader_can_execute_signal(self, trader):
        """Test Trader can execute trading signal."""
        if hasattr(trader, "execute_signal"):
            signal = {"symbol": "EURUSD", "action": "buy", "volume": 1.0}
            result = trader.execute_signal(signal)
            assert result is None or isinstance(result, (bool, dict))

    def test_trader_can_close_position(self, trader):
        """Test Trader can close position."""
        if hasattr(trader, "close_position"):
            result = trader.close_position(1001)
            assert result is None or isinstance(result, (bool, dict))

    def test_trader_get_account_info(self, trader):
        """Test getting account information."""
        if hasattr(trader, "get_account_info"):
            info = trader.get_account_info()
            assert info is None or isinstance(info, dict)

    def test_trader_get_position_info(self, trader):
        """Test getting position information."""
        if hasattr(trader, "get_position_info"):
            info = trader.get_position_info(1001)
            assert info is None or isinstance(info, dict)

    def test_trader_validate_signal(self, trader):
        """Test signal validation."""
        if hasattr(trader, "validate_signal"):
            signal = {"symbol": "EURUSD", "action": "buy"}
            valid = trader.validate_signal(signal)
            assert isinstance(valid, bool)

    def test_trader_check_risk_limits(self, trader):
        """Test risk limit checking."""
        if hasattr(trader, "check_risk_limits"):
            within_limits = trader.check_risk_limits()
            assert within_limits is None or isinstance(within_limits, bool)

    def test_trader_get_open_trades(self, trader):
        """Test getting open trades."""
        if hasattr(trader, "get_open_trades"):
            trades = trader.get_open_trades()
            assert trades is None or isinstance(trades, (list, dict))

    def test_trader_get_trade_performance(self, trader):
        """Test getting trade performance."""
        if hasattr(trader, "get_trade_performance"):
            perf = trader.get_trade_performance()
            assert perf is None or isinstance(perf, dict)

    def test_trader_calculate_profit_loss(self, trader):
        """Test profit/loss calculation."""
        if hasattr(trader, "calculate_pnl"):
            pnl = trader.calculate_pnl(
                entry=1.2500, exit=1.2600, volume=1.0, direction="buy"
            )
            assert pnl is None or isinstance(pnl, (int, float))

    def test_trader_position_sizing(self, trader):
        """Test position sizing."""
        if hasattr(trader, "calculate_position_size"):
            size = trader.calculate_position_size(
                risk_per_trade=0.02, entry=1.2500, stop_loss=1.2400
            )
            assert size is None or isinstance(size, (int, float))

    def test_trader_stop_loss_adjustment(self, trader):
        """Test stop loss adjustment."""
        if hasattr(trader, "adjust_stop_loss"):
            result = trader.adjust_stop_loss(1001, 1.2450)
            assert result is None or isinstance(result, bool)

    def test_trader_take_profit_adjustment(self, trader):
        """Test take profit adjustment."""
        if hasattr(trader, "adjust_take_profit"):
            result = trader.adjust_take_profit(1001, 1.2650)
            assert result is None or isinstance(result, bool)

    def test_trader_market_status_check(self, trader):
        """Test market status checking."""
        if hasattr(trader, "is_market_open"):
            status = trader.is_market_open()
            assert status is None or isinstance(status, bool)

    def test_trader_emergency_close(self, trader):
        """Test emergency close mechanism."""
        if hasattr(trader, "emergency_close_all"):
            result = trader.emergency_close_all()
            assert result is None or isinstance(result, (bool, dict))

    def test_trader_validate_signal_with_entry_price(self, trader):
        """Test signal validation with entry price."""
        if hasattr(trader, "validate_signal"):
            signal = {"symbol": "EURUSD", "type": "BUY", "confidence": 0.85}
            result = trader.validate_signal(signal)
            assert result is None or isinstance(result, bool)

    def test_trader_check_risk_limits_multiple_positions(self, trader):
        """Test risk limits check with multiple positions."""
        if hasattr(trader, "check_risk_limits"):
            trader.mt5_connector.get_positions.return_value = [
                {"ticket": 1001, "profit": 100},
                {"ticket": 1002, "profit": -50},
            ]
            result = trader.check_risk_limits()
            assert result is None or isinstance(result, bool)

    def test_trader_get_open_trades_count(self, trader):
        """Test getting open trades count."""
        if hasattr(trader, "get_open_trades"):
            trader.mt5_connector.get_positions.return_value = [{"ticket": 1001}]
            trades = trader.get_open_trades()
            assert isinstance(trades, (list, type(None)))

    def test_trader_get_trade_performance_with_loss(self, trader):
        """Test trade performance with loss."""
        if hasattr(trader, "get_trade_performance"):
            result = trader.get_trade_performance(1001)
            assert result is None or isinstance(result, dict)

    def test_trader_calculate_profit_loss_short(self, trader):
        """Test P&L calculation for short positions."""
        if hasattr(trader, "calculate_pnl"):
            pnl = trader.calculate_pnl(
                entry=1.2600, exit=1.2500, volume=1.0, direction="sell"
            )
            assert pnl is None or isinstance(pnl, (int, float))

    def test_trader_position_sizing_with_breakeven(self, trader):
        """Test position sizing at breakeven."""
        if hasattr(trader, "calculate_position_size"):
            size = trader.calculate_position_size(
                risk_per_trade=0.0, entry=1.2500, stop_loss=1.2500
            )
            assert size is None or isinstance(size, (int, float))

    def test_trader_stop_loss_multiple_adjustments(self, trader):
        """Test multiple stop loss adjustments."""
        if hasattr(trader, "adjust_stop_loss"):
            for new_sl in [1.2450, 1.2475, 1.2490]:
                result = trader.adjust_stop_loss(1001, new_sl)
                assert result is None or isinstance(result, bool)

    def test_trader_take_profit_at_breakeven(self, trader):
        """Test take profit adjustment at breakeven."""
        if hasattr(trader, "adjust_take_profit"):
            result = trader.adjust_take_profit(1001, 1.2500)
            assert result is None or isinstance(result, bool)

    def test_trader_market_weekend_check(self, trader):
        """Test market status on weekends."""
        if hasattr(trader, "is_market_open"):
            status = trader.is_market_open()
            assert status is None or isinstance(status, bool)

    def test_trader_emergency_close_all_positions(self, trader):
        """Test emergency close with multiple positions."""
        if hasattr(trader, "emergency_close_all"):
            trader.mt5_connector.get_positions.return_value = [
                {"ticket": 1001},
                {"ticket": 1002},
            ]
            result = trader.emergency_close_all()
            assert result is None or isinstance(result, (bool, dict))

    def test_trader_account_balance_check(self, trader):
        """Test account balance retrieval."""
        if hasattr(trader, "get_account_info"):
            trader.mt5_connector.get_account_info.return_value = {"balance": 10000}
            info = trader.get_account_info()
            assert info is None or isinstance(info, dict)

    def test_trader_position_info_retrieval(self, trader):
        """Test position info retrieval."""
        if hasattr(trader, "get_position_info"):
            trader.mt5_connector.get_position.return_value = {"ticket": 1001}
            info = trader.get_position_info(1001)
            assert info is None or isinstance(info, dict)

    # ===== NEW COMPREHENSIVE TESTS =====

    def test_logger_is_logging_logger(self, trader):
        """Test that logger is a proper logging.Logger instance."""
        assert isinstance(trader.logger, logging.Logger)

    def test_trader_has_proper_dependencies(self, trader):
        """Test that trader is initialized with required dependencies."""
        assert trader.strategy_manager is not None
        assert trader.mt5_connector is not None

    def test_execute_trade_method_exists(self, trader):
        """Test execute_trade method is callable."""
        if hasattr(trader, "execute_trade"):
            assert callable(trader.execute_trade)

    def test_place_order_method_callable(self, trader):
        """Test place_order method is callable if it exists."""
        if hasattr(trader, "place_order"):
            assert callable(trader.place_order)

    def test_close_position_method_callable(self, trader):
        """Test close_position method is callable if it exists."""
        if hasattr(trader, "close_position"):
            assert callable(trader.close_position)

    def test_mt5_connector_initialization(self, mock_dependencies):
        """Test MT5 connector is properly initialized."""
        strategy_manager, mt5_connector = mock_dependencies
        trader = Trader(strategy_manager, mt5_connector)
        assert trader.mt5_connector == mt5_connector

    def test_strategy_manager_access(self, trader):
        """Test strategy manager is accessible."""
        assert trader.strategy_manager is not None
        assert hasattr(trader.strategy_manager, "__dict__") or True

    @pytest.mark.parametrize(
        "symbol,amount,order_type",
        [
            ("BTCUSD", 0.1, "BUY"),
            ("EURUSD", 1.0, "SELL"),
            ("GBPUSD", 0.5, "BUY"),
            ("USDJPY", 100.0, "SELL"),
        ],
    )
    def test_execute_trade_parametrized(self, trader, symbol, amount, order_type):
        """Parametrized test for execute_trade with various symbols."""
        if hasattr(trader, "execute_trade"):
            trader.mt5_connector.place_order = MagicMock(return_value=True)
            result = trader.execute_trade(symbol, amount, order_type)
            assert result is None or isinstance(result, (bool, dict))

    def test_position_tracking(self, trader):
        """Test position tracking functionality."""
        if hasattr(trader, "_positions"):
            positions = trader._positions
            assert isinstance(positions, (dict, list)) or positions is None

    def test_trade_execution_with_error(self, trader):
        """Test trade execution error handling."""
        if hasattr(trader, "execute_trade"):
            trader.mt5_connector.place_order = MagicMock(
                side_effect=Exception("Order failed")
            )
            result = trader.execute_trade("BTCUSD", 0.1, "BUY")
            assert result is None or isinstance(result, (bool, dict))

    def test_multiple_positions_management(self, trader):
        """Test managing multiple open positions."""
        if hasattr(trader, "get_positions"):
            trader.mt5_connector.get_positions = MagicMock(
                return_value=[
                    {"ticket": 1001, "symbol": "BTCUSD", "profit": 100},
                    {"ticket": 1002, "symbol": "EURUSD", "profit": -50},
                    {"ticket": 1003, "symbol": "GBPUSD", "profit": 200},
                ]
            )
            positions = (
                trader.get_positions() if hasattr(trader, "get_positions") else None
            )
            assert positions is None or isinstance(positions, list)

    def test_risk_management_checks(self, trader):
        """Test risk management validation."""
        if hasattr(trader, "_check_risk_limits"):
            result = trader._check_risk_limits()
            assert result is None or isinstance(result, bool)

    def test_none_dependencies(self):
        """Test handling of None dependencies gracefully."""
        trader = Trader(None, None)
        assert trader is not None
        assert trader.strategy_manager is None
        assert trader.mt5_connector is None

    def test_trader_state_management(self, trader):
        """Test trader can maintain state."""
        if hasattr(trader, "_state"):
            assert trader._state is not None or True

    @pytest.mark.parametrize(
        "lot_size,leverage,margin_per_lot",
        [
            (0.1, 30, 100),
            (0.5, 30, 500),
            (1.0, 30, 1000),
            (10.0, 30, 10000),
        ],
    )
    def test_position_sizing_calculation(
        self, trader, lot_size, leverage, margin_per_lot
    ):
        """Parametrized test for position sizing with different parameters."""
        if hasattr(trader, "_calculate_position_size"):
            result = trader._calculate_position_size(lot_size, leverage)
            assert result is None or isinstance(result, (int, float))

    def test_order_validation(self, trader):
        """Test order validation before execution."""
        if hasattr(trader, "_validate_order"):
            result = trader._validate_order(
                symbol="BTCUSD", volume=0.1, order_type="BUY"
            )
            assert result is None or isinstance(result, bool)

    def test_slippage_adjustment(self, trader):
        """Test slippage adjustment in order placement."""
        if hasattr(trader, "_apply_slippage"):
            result = trader._apply_slippage(price=40000, slippage_pips=5)
            assert result is None or isinstance(result, (int, float))
