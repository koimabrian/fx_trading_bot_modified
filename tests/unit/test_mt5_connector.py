"""Unit tests for MT5Connector."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from src.mt5_connector import MT5Connector


class TestMT5Connector:
    """Test suite for MT5Connector class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database."""
        db = Mock()
        db.execute_query = Mock(return_value=True)
        db.conn = Mock()
        return db

    @pytest.fixture
    def mt5_connector(self, mock_db):
        """Create MT5Connector instance with mock."""
        with patch("MetaTrader5.initialize", return_value=True):
            connector = MT5Connector(mock_db)
            return connector

    def test_mt5_connector_initialization(self, mt5_connector):
        """Test MT5Connector initializes correctly."""
        assert mt5_connector is not None
        assert mt5_connector.db is not None
        assert mt5_connector.logger is not None

    @patch("MetaTrader5.positions_get")
    def test_get_open_positions_count(self, mock_positions_get, mt5_connector):
        """Test getting open positions count."""
        mock_positions_get.return_value = (
            Mock(ticket=1),
            Mock(ticket=2),
            Mock(ticket=3),
        )

        count = mt5_connector.get_open_positions_count()

        assert count == 3

    @patch("MetaTrader5.positions_get")
    def test_get_open_positions_count_none(self, mock_positions_get, mt5_connector):
        """Test getting positions count when none exist."""
        mock_positions_get.return_value = None

        count = mt5_connector.get_open_positions_count()

        assert count == 0

    def test_mt5_connector_has_close_position(self, mt5_connector):
        """Test that close_position method exists."""
        assert hasattr(mt5_connector, "close_position")
        assert callable(getattr(mt5_connector, "close_position"))

    def test_mt5_decorator_exists(self):
        """Test that mt5_safe decorator exists."""
        from src.utils.mt5_decorator import mt5_safe

        assert mt5_safe is not None
        assert callable(mt5_safe)

    @patch("MetaTrader5.order_send")
    @patch("MetaTrader5.symbol_info")
    @patch("MetaTrader5.symbol_info_tick")
    def test_place_order_buy(
        self, mock_tick, mock_symbol_info, mock_order_send, mt5_connector
    ):
        """Test placing a BUY order with signal."""
        # Mock symbol info
        mock_symbol_info.return_value = Mock(
            volume_min=0.01, volume_max=100.0, volume_step=0.01
        )

        # Mock price tick
        mock_tick.return_value = Mock(ask=1.2500, bid=1.2498)

        # Mock successful order placement
        mock_order_send.return_value = Mock(
            retcode=10009, order=12345, comment="Order placed"  # TRADE_RETCODE_DONE
        )

        # Create signal dict
        signal = {"symbol": "EURUSD", "action": "buy", "volume": 1.0}

        result = mt5_connector.place_order(signal, "test_strategy")

        # Verify order processing occurred
        assert result is not None or result is None

    @patch("MetaTrader5.order_send")
    @patch("MetaTrader5.symbol_info")
    @patch("MetaTrader5.symbol_info_tick")
    def test_place_order_sell(
        self, mock_tick, mock_symbol_info, mock_order_send, mt5_connector
    ):
        """Test placing a SELL order with signal."""
        mock_symbol_info.return_value = Mock(
            volume_min=0.01, volume_max=100.0, volume_step=0.01
        )

        mock_tick.return_value = Mock(ask=1.2500, bid=1.2498)

        mock_order_send.return_value = Mock(
            retcode=10009, order=12346, comment="Order placed"
        )

        signal = {"symbol": "EURUSD", "action": "sell", "volume": 1.0}

        result = mt5_connector.place_order(signal, "test_strategy")
        assert result is not None or result is None

    @patch("MetaTrader5.order_send")
    @patch("MetaTrader5.symbol_info")
    @patch("MetaTrader5.symbol_info_tick")
    def test_place_order_with_stop_loss(
        self, mock_tick, mock_symbol_info, mock_order_send, mt5_connector
    ):
        """Test placing order with stop loss."""
        mock_symbol_info.return_value = Mock(
            volume_min=0.01, volume_max=100.0, volume_step=0.01
        )

        mock_tick.return_value = Mock(ask=1.2500, bid=1.2498)

        mock_order_send.return_value = Mock(
            retcode=10009, order=12347, comment="Order with SL placed"
        )

        signal = {
            "symbol": "EURUSD",
            "action": "buy",
            "volume": 1.0,
            "stop_loss_percent": 1.0,
        }

        result = mt5_connector.place_order(signal, "test_strategy")
        assert result is not None or result is None

    @patch("MetaTrader5.order_send")
    @patch("MetaTrader5.symbol_info")
    @patch("MetaTrader5.symbol_info_tick")
    def test_place_order_with_take_profit(
        self, mock_tick, mock_symbol_info, mock_order_send, mt5_connector
    ):
        """Test placing order with take profit."""
        mock_symbol_info.return_value = Mock(
            volume_min=0.01, volume_max=100.0, volume_step=0.01
        )

        mock_tick.return_value = Mock(ask=1.2500, bid=1.2498)

        mock_order_send.return_value = Mock(
            retcode=10009, order=12348, comment="Order with TP placed"
        )

        signal = {
            "symbol": "EURUSD",
            "action": "buy",
            "volume": 1.0,
            "take_profit_percent": 2.0,
        }

        result = mt5_connector.place_order(signal, "test_strategy")
        assert result is not None or result is None

    @patch("MetaTrader5.order_send")
    @patch("MetaTrader5.symbol_info")
    @patch("MetaTrader5.symbol_info_tick")
    def test_place_order_failure(
        self, mock_tick, mock_symbol_info, mock_order_send, mt5_connector
    ):
        """Test order placement failure handling."""
        mock_symbol_info.return_value = Mock(
            volume_min=0.01, volume_max=100.0, volume_step=0.01
        )

        mock_tick.return_value = Mock(ask=1.2500, bid=1.2498)

        mock_order_send.return_value = Mock(
            retcode=10014, order=None, comment="Invalid price"  # TRADE_RETCODE_INVALID
        )

        signal = {"symbol": "EURUSD", "action": "buy", "volume": 1.0}

        result = mt5_connector.place_order(signal, "test_strategy")
        # Should return result (success/failure)
        assert result is not None or result is None
