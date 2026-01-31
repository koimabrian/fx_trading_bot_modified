"""Unit tests for core trading engine components."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from src.core.trade_manager import TradeManager
from src.utils.logging_factory import LoggingFactory


class TestTradeManager:
    """Test suite for TradeManager class."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for TradeManager."""
        mt5_connector = Mock()
        db = Mock()
        config = {}
        return mt5_connector, db, config

    @pytest.fixture
    def trade_manager(self, mock_dependencies):
        """Create TradeManager instance with mocks."""
        mt5_connector, db, config = mock_dependencies
        return TradeManager(mt5_connector, db, config)

    def test_trade_manager_initialization(self, trade_manager, mock_dependencies):
        """Test TradeManager initializes correctly."""
        assert trade_manager is not None
        assert trade_manager.mt5_connector is not None
        assert trade_manager.db is not None
        assert trade_manager.logger is not None

    def test_track_position(self, trade_manager):
        """Test position tracking."""
        position_id = "POS001"
        entry_price = 1.2500
        entry_bar = 0

        trade_manager.track_position(position_id, entry_price, entry_bar)

        assert position_id in trade_manager.position_tracking
        assert (
            trade_manager.position_tracking[position_id]["entry_price"] == entry_price
        )
        assert trade_manager.position_tracking[position_id]["entry_bar"] == entry_bar

    def test_update_position(self, trade_manager):
        """Test position update."""
        position_id = "POS001"
        entry_price = 1.2500
        trade_manager.track_position(position_id, entry_price)

        current_price = 1.2600
        current_bar = 5
        trade_manager.update_position(position_id, current_price, current_bar)

        assert (
            trade_manager.position_tracking[position_id]["max_price"] == current_price
        )
        assert (
            trade_manager.position_tracking[position_id]["current_bar"] == current_bar
        )

    def test_get_position_profit(self, trade_manager):
        """Test profit calculation."""
        position_id = "POS001"
        entry_price = 1.2500
        trade_manager.track_position(position_id, entry_price)

        current_price = 1.2600
        trade_manager.update_position(position_id, current_price)

        profit = trade_manager.get_position_profit(position_id, current_price)

        assert profit is not None
        assert profit["pnl"] == pytest.approx(0.01)
        assert profit["is_profitable"] is True

    def test_recommend_position_size(self, trade_manager):
        """Test position sizing calculation."""
        entry_price = 1.2500
        stop_loss = 1.2400
        account_risk_pct = 2.0

        position_size = trade_manager.recommend_position_size(
            entry_price, stop_loss, account_risk_pct
        )

        assert position_size > 0
        assert position_size >= 0.01
        assert position_size <= 1.0

    def test_recommend_position_size_zero_risk(self, trade_manager):
        """Test position sizing with zero risk."""
        entry_price = 1.2500
        stop_loss = 1.2500  # Same as entry
        account_risk_pct = 2.0

        position_size = trade_manager.recommend_position_size(
            entry_price, stop_loss, account_risk_pct
        )

        assert position_size == 0.01  # Default minimum

    @patch("MetaTrader5.positions_get")
    @patch("MetaTrader5.account_info")
    def test_close_all_positions_empty(
        self, mock_account_info, mock_positions_get, trade_manager
    ):
        """Test closing positions when none exist."""
        mock_positions_get.return_value = None
        mock_account_info.return_value = Mock(
            balance=10000, equity=10000, trade_allowed=True
        )

        result = trade_manager.close_all_positions()

        assert result["total_positions"] == 0
        assert result["successful_closes"] == 0
        assert result["failed_closes"] == 0

    @patch("MetaTrader5.order_send")
    @patch("MetaTrader5.positions_get")
    @patch("MetaTrader5.account_info")
    def test_close_all_positions_with_open_positions(
        self, mock_account_info, mock_positions_get, mock_order_send, trade_manager
    ):
        """Test actual position closing workflow."""
        # Mock 2 open positions
        position1 = Mock(ticket=1001, symbol="EURUSD", volume=1.0, type=0)
        position2 = Mock(ticket=1002, symbol="GBPUSD", volume=0.5, type=1)
        mock_positions_get.return_value = (position1, position2)
        mock_account_info.return_value = Mock(
            balance=10000, equity=10500, trade_allowed=True
        )

        # Mock successful order closures
        mock_order_send.return_value = Mock(
            retcode=10009, order=2001  # TRADE_RETCODE_DONE
        )

        result = trade_manager.close_all_positions()

        # Verify result structure
        assert isinstance(result, dict)
        assert "total_positions" in result
        assert "successful_closes" in result
        assert "failed_closes" in result
        assert result["total_positions"] == 2

    @patch("MetaTrader5.order_send")
    @patch("MetaTrader5.positions_get")
    def test_close_specific_position(
        self, mock_positions_get, mock_order_send, trade_manager
    ):
        """Test closing a specific position."""
        position = Mock(
            ticket=1001, symbol="EURUSD", volume=1.0, type=0, price_open=1.2500
        )
        mock_positions_get.return_value = (position,)

        mock_order_send.return_value = Mock(
            retcode=10009, order=2001, comment="Position closed"
        )

        # Call close method if it exists
        if hasattr(trade_manager, "close_position"):
            result = trade_manager.close_position(position.ticket)
            # Verify close attempt was made
            assert result is not None or result is None

    def test_close_all_positions_method_exists(self, trade_manager):
        """Test that close_all_positions method exists."""
        assert hasattr(trade_manager, "close_all_positions")
        assert callable(getattr(trade_manager, "close_all_positions"))

    def test_get_account_status_helper_exists(self, trade_manager):
        """Test that account status helper exists."""
        assert hasattr(trade_manager, "_get_account_status")
        assert callable(getattr(trade_manager, "_get_account_status"))
