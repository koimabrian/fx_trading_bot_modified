"""Unit tests for TradeSyncer class.

Tests the MT5 trade synchronization functionality including
deals, orders, positions, and reconciliation.
"""

import sys
import unittest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

# Mock MetaTrader5 before importing TradeSyncer
sys.modules['MetaTrader5'] = MagicMock()

from src.core.trade_syncer import TradeSyncer


class TestTradeSyncer(unittest.TestCase):
    """Test suite for TradeSyncer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = Mock()
        self.mock_mt5 = Mock()
        self.syncer = TradeSyncer(self.mock_db, self.mock_mt5)

    def test_init(self):
        """Test TradeSyncer initialization."""
        self.assertIsNotNone(self.syncer.db)
        self.assertIsNotNone(self.syncer.mt5)
        self.assertIsNotNone(self.syncer.logger)

    @patch('src.core.trade_syncer.mt5')
    def test_sync_deals_from_mt5_success(self, mock_mt5_module):
        """Test successful deal synchronization."""
        # Mock deal object
        mock_deal = Mock()
        mock_deal.ticket = 12345
        mock_deal.symbol = "EURUSD"
        mock_deal.type = 0  # BUY
        mock_deal.volume = 0.1
        mock_deal.price = 1.1000
        mock_deal.profit = 10.5
        mock_deal.time = int(datetime.now().timestamp())
        mock_deal.order = 12344
        mock_deal.magic = 0
        mock_deal.swap = 0
        mock_deal.commission = 0
        mock_deal.comment = ""
        
        mock_mt5_module.history_deals_get.return_value = [mock_deal]
        
        # Mock database responses
        mock_result = Mock()
        mock_result.fetchone.return_value = {"id": 1}
        self.mock_db.execute_query.return_value = mock_result
        
        result = self.syncer.sync_deals_from_mt5(days_back=7)
        
        self.assertEqual(result, 1)
        self.assertTrue(mock_mt5_module.history_deals_get.called)

    @patch('src.core.trade_syncer.mt5')
    def test_sync_deals_from_mt5_no_deals(self, mock_mt5_module):
        """Test deal synchronization when no deals exist."""
        mock_mt5_module.history_deals_get.return_value = None
        
        result = self.syncer.sync_deals_from_mt5(days_back=7)
        
        self.assertEqual(result, 0)

    @patch('src.core.trade_syncer.mt5')
    def test_sync_orders_from_mt5_success(self, mock_mt5_module):
        """Test successful order synchronization."""
        # Mock order object
        mock_order = Mock()
        mock_order.ticket = 23456
        mock_order.symbol = "GBPUSD"
        mock_order.type = 0  # BUY
        mock_order.volume_initial = 0.1
        mock_order.price_open = 1.2500
        mock_order.price_current = 1.2510
        mock_order.time_setup = int(datetime.now().timestamp())
        mock_order.state = 4  # FILLED
        mock_order.magic = 0
        mock_order.comment = ""
        
        mock_mt5_module.history_orders_get.return_value = [mock_order]
        
        # Mock database responses
        mock_result = Mock()
        mock_result.fetchone.return_value = {"id": 1}
        self.mock_db.execute_query.return_value = mock_result
        
        result = self.syncer.sync_orders_from_mt5(days_back=7)
        
        self.assertEqual(result, 1)
        self.assertTrue(mock_mt5_module.history_orders_get.called)

    @patch('src.core.trade_syncer.mt5')
    def test_sync_open_positions_success(self, mock_mt5_module):
        """Test successful open position synchronization."""
        # Mock position object
        mock_position = Mock()
        mock_position.ticket = 34567
        mock_position.symbol = "USDJPY"
        mock_position.type = 1  # SELL
        mock_position.volume = 0.2
        mock_position.price_open = 110.50
        mock_position.price_current = 110.40
        mock_position.profit = 10.0
        mock_position.swap = -0.5
        mock_position.commission = -1.0
        mock_position.time = int(datetime.now().timestamp())
        mock_position.magic = 0
        mock_position.comment = ""
        
        mock_mt5_module.positions_get.return_value = [mock_position]
        
        # Mock database responses
        mock_result = Mock()
        mock_result.fetchone.return_value = {"id": 1}
        self.mock_db.execute_query.return_value = mock_result
        
        result = self.syncer.sync_open_positions()
        
        self.assertEqual(result, 1)
        self.assertTrue(mock_mt5_module.positions_get.called)

    @patch('src.core.trade_syncer.mt5')
    def test_reconcile_with_database(self, mock_mt5_module):
        """Test database reconciliation with MT5."""
        # Mock MT5 positions
        mock_position = Mock()
        mock_position.ticket = 45678
        mock_mt5_module.positions_get.return_value = [mock_position]
        
        # Mock database query results
        mock_result = Mock()
        # Simulate a position that's open in DB but not in MT5
        mock_result.fetchall.return_value = [
            {"order_id": 99999, "deal_id": None, "status": "open", "id": 1}
        ]
        self.mock_db.execute_query.return_value = mock_result
        
        # Mock upsert_position to succeed
        self.syncer._upsert_position = Mock(return_value=True)
        
        result = self.syncer.reconcile_with_database()
        
        self.assertIn("closed_in_mt5", result)
        self.assertIn("missing_in_db", result)
        self.assertIn("synced", result)
        self.assertEqual(len(result["closed_in_mt5"]), 1)
        self.assertEqual(result["closed_in_mt5"][0], 99999)

    def test_mark_trade_closed(self):
        """Test marking a trade as closed."""
        self.syncer._mark_trade_closed(1)
        
        # Verify execute_query was called with correct parameters
        self.mock_db.execute_query.assert_called_once()
        call_args = self.mock_db.execute_query.call_args
        self.assertIn("UPDATE live_trades", call_args[0][0])
        self.assertIn("closed", call_args[0][0])

    @patch('src.core.trade_syncer.mt5')
    def test_upsert_deal_symbol_not_in_db(self, mock_mt5_module):
        """Test upserting a deal when symbol is not in tradable_pairs."""
        mock_deal = Mock()
        mock_deal.ticket = 12345
        mock_deal.symbol = "UNKNOWN"
        
        # Mock database to return None for symbol lookup
        mock_result = Mock()
        mock_result.fetchone.return_value = None
        self.mock_db.execute_query.return_value = mock_result
        
        result = self.syncer._upsert_deal(mock_deal)
        
        self.assertFalse(result)

    @patch('src.core.trade_syncer.mt5')
    def test_sync_deals_exception_handling(self, mock_mt5_module):
        """Test exception handling in sync_deals_from_mt5."""
        mock_mt5_module.history_deals_get.side_effect = Exception("MT5 Error")
        
        result = self.syncer.sync_deals_from_mt5(days_back=7)
        
        self.assertEqual(result, 0)

    @patch('src.core.trade_syncer.mt5')
    def test_sync_orders_exception_handling(self, mock_mt5_module):
        """Test exception handling in sync_orders_from_mt5."""
        mock_mt5_module.history_orders_get.side_effect = Exception("MT5 Error")
        
        result = self.syncer.sync_orders_from_mt5(days_back=7)
        
        self.assertEqual(result, 0)

    @patch('src.core.trade_syncer.mt5')
    def test_sync_positions_exception_handling(self, mock_mt5_module):
        """Test exception handling in sync_open_positions."""
        mock_mt5_module.positions_get.side_effect = Exception("MT5 Error")
        
        result = self.syncer.sync_open_positions()
        
        self.assertEqual(result, 0)


if __name__ == '__main__':
    unittest.main()
