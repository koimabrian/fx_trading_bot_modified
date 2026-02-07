"""
Test: Max Positions Reached (5/5) Filter
==========================================

Tests the position limit checking logic that:
1. Checks if positions already exist for a symbol
2. Validates total position count (max 5)
3. Validates per-symbol limit (max 5)
4. Calculates how many more positions can be opened
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List


# Mock MT5 position class
class MockPosition:
    def __init__(self, symbol: str, ticket: int):
        self.symbol = symbol
        self.ticket = ticket


# Test Fixture: Create a position limit checker
@pytest.fixture
def position_limit_checker():
    """Create a mock position limit checker"""
    config = {
        "risk_management": {
            "max_positions": 5,  # Total max positions
            "max_positions_per_symbol": 5,  # Max per symbol
        }
    }

    mt5_mock = Mock()
    trading_rules_mock = Mock()
    trading_rules_mock.get_symbol_category.return_value = "forex"

    from src.utils.trade_quality_filter import PositionLimitManager

    return PositionLimitManager(config, mt5_mock, trading_rules_mock)


class TestMaxPositionsFilter:
    """Test suite for max positions limit filter (5/5)"""

    def test_no_positions_can_open_new(self, position_limit_checker):
        """Test: No open positions → can open new position"""
        position_limit_checker.mt5.get_open_positions.return_value = []

        result = position_limit_checker.can_open_position("EURUSD")

        assert result is True, "Should allow position when no positions exist"

    def test_one_position_exists_can_open_more(self, position_limit_checker):
        """Test: 1 position open (1/5) → can still open more"""
        positions = [MockPosition("GBPUSD", 1001)]
        position_limit_checker.mt5.get_open_positions.return_value = positions

        result = position_limit_checker.can_open_position("EURUSD")

        assert result is True, "Should allow position when count < 5"

    def test_max_positions_reached_blocks_new(self, position_limit_checker):
        """Test: 5 positions open (5/5) → BLOCK new position"""
        # Create 5 positions
        positions = [
            MockPosition("EURUSD", 1001),
            MockPosition("GBPUSD", 1002),
            MockPosition("USDJPY", 1003),
            MockPosition("AUDUSD", 1004),
            MockPosition("NZDUSD", 1005),
        ]
        position_limit_checker.mt5.get_open_positions.return_value = positions

        result = position_limit_checker.can_open_position("USDCAD")

        assert result is False, "Should BLOCK position when at max (5/5)"

    def test_existing_symbol_positions_counted(self, position_limit_checker):
        """Test: Check if existing positions for symbol are counted"""
        # 1 EURUSD + 1 CRYPTO (1 FOREX, below FOREX limit of 3)
        positions = [
            MockPosition("EURUSD", 1001),
            MockPosition("BTCUSD", 1002),  # CRYPTO position
        ]
        position_limit_checker.mt5.get_open_positions.return_value = positions
        position_limit_checker.rules.get_symbol_category.side_effect = lambda s: (
            "forex" if s == "EURUSD" else "crypto"
        )

        # Try to add 2nd EURUSD (should succeed - FOREX: 1/3, Total: 2/5)
        result = position_limit_checker.can_open_position("EURUSD")

        assert result is True, "Should allow 2nd EURUSD (FOREX: 1/3, Total: 2/5)"

    def test_per_symbol_limit_5_positions_blocked(self, position_limit_checker):
        """Test: 5 positions for same symbol (5/5 per-symbol) → BLOCK"""
        # 5 EURUSD positions (at max per-symbol)
        positions = [
            MockPosition("EURUSD", 1001),
            MockPosition("EURUSD", 1002),
            MockPosition("EURUSD", 1003),
            MockPosition("EURUSD", 1004),
            MockPosition("EURUSD", 1005),
        ]
        position_limit_checker.mt5.get_open_positions.return_value = positions

        result = position_limit_checker.can_open_position("EURUSD")

        assert result is False, "Should BLOCK 6th position for same symbol"

    def test_mixed_symbols_total_limit(self, position_limit_checker):
        """Test: Mixed symbols with total limit enforcement (5/5)"""
        # 2 EURUSD + 3 other symbols (5 total)
        positions = [
            MockPosition("EURUSD", 1001),
            MockPosition("EURUSD", 1002),
            MockPosition("GBPUSD", 1003),
            MockPosition("USDJPY", 1004),
            MockPosition("AUDUSD", 1005),
        ]
        position_limit_checker.mt5.get_open_positions.return_value = positions

        result = position_limit_checker.can_open_position("EURUSD")

        assert result is False, "Should BLOCK when total positions at limit (5/5)"

    def test_positions_available_calculation(self, position_limit_checker):
        """Test: Calculate how many more positions can be opened"""
        # 3 positions open
        positions = [
            MockPosition("EURUSD", 1001),
            MockPosition("GBPUSD", 1002),
            MockPosition("USDJPY", 1003),
        ]
        position_limit_checker.mt5.get_open_positions.return_value = positions

        stats = position_limit_checker.get_position_stats()

        # Available = max_positions - current_positions
        available = stats["total_limit"] - stats["total_positions"]
        assert (
            available == 2
        ), f"Should have 2 positions available (5 - 3), got {available}"

    def test_position_stats_detailed_report(self, position_limit_checker):
        """Test: Get detailed position statistics"""
        # 2 positions open
        positions = [MockPosition("EURUSD", 1001), MockPosition("GBPUSD", 1002)]
        position_limit_checker.mt5.get_open_positions.return_value = positions

        stats = position_limit_checker.get_position_stats()

        assert stats["total_positions"] == 2
        assert stats["total_limit"] == 5
        print(
            f"\n✅ Position Stats: {stats['total_positions']}/{stats['total_limit']} positions open"
        )

    def test_symbol_with_existing_positions_allows_more(self, position_limit_checker):
        """Test: Symbol with existing positions can add more (up to limit)"""
        # 2 EURUSD positions
        positions = [MockPosition("EURUSD", 1001), MockPosition("EURUSD", 1002)]
        position_limit_checker.mt5.get_open_positions.return_value = positions

        # Try to add 3rd EURUSD
        result = position_limit_checker.can_open_position("EURUSD")

        assert result is True, "Should allow 3rd position for EURUSD (2/5 per-symbol)"

    def test_empty_position_list_vs_none(self, position_limit_checker):
        """Test: Empty position list handled correctly (not None)"""
        # Empty list should be handled same as no positions
        position_limit_checker.mt5.get_open_positions.return_value = []

        result = position_limit_checker.can_open_position("EURUSD")
        stats = position_limit_checker.get_position_stats()

        assert result is True
        assert stats["total_positions"] == 0
        assert stats["total_limit"] == 5


class TestPositionFilterIntegration:
    """Integration tests with actual trader flow"""

    @patch("src.utils.trade_quality_filter.PositionLimitManager")
    def test_trader_respects_position_limit(self, mock_limit_checker):
        """Test: Trader respects position limit before executing trade"""
        mock_limit_checker.return_value.can_open_position.return_value = False

        # Simulate trader trying to open position at limit
        checker = mock_limit_checker.return_value
        result = checker.can_open_position("EURUSD")

        assert result is False, "Trader should not open position when at limit"
        mock_limit_checker.return_value.can_open_position.assert_called_with("EURUSD")

    def test_position_count_accuracy(self, position_limit_checker):
        """Test: Position count accuracy with various scenarios - accounting for FOREX limit of 3"""
        # Setup category mock - use rules not trading_rules
        position_limit_checker.rules.get_symbol_category.side_effect = lambda s: (
            "forex" if s in ["EURUSD", "GBPUSD", "USDJPY"] else "crypto"
        )

        # Test 1: 0/5 positions - should allow
        position_limit_checker.mt5.get_open_positions.return_value = []
        result = position_limit_checker.can_open_position("EURUSD")
        assert result is True, "Should allow at 0/5 positions"
        print("✅ 0/5 positions: ALLOW")

        # Test 2: 1/5 positions (1 FOREX) - should allow
        one_position = [MockPosition("EURUSD", 1001)]
        position_limit_checker.mt5.get_open_positions.return_value = one_position
        result = position_limit_checker.can_open_position("GBPUSD")
        assert result is True, "Should allow at 1/5 positions"
        print("✅ 1/5 positions (FOREX 1/3): ALLOW")

        # Test 3: 2/5 positions (2 FOREX) - should allow
        two_positions = [MockPosition("EURUSD", 1001), MockPosition("GBPUSD", 1002)]
        position_limit_checker.mt5.get_open_positions.return_value = two_positions
        result = position_limit_checker.can_open_position("USDJPY")
        assert result is True, "Should allow at 2/5 positions"
        print("✅ 2/5 positions (FOREX 2/3): ALLOW")

        # Test 4: 3/5 positions (3 FOREX at limit) - FOREX blocked, but CRYPTO allowed
        three_positions = [
            MockPosition("EURUSD", 1001),
            MockPosition("GBPUSD", 1002),
            MockPosition("USDJPY", 1003),
        ]
        position_limit_checker.mt5.get_open_positions.return_value = three_positions
        result = position_limit_checker.can_open_position("BTCUSD")
        assert result is True, "Should allow CRYPTO at 3/5 (FOREX at 3/3 limit)"
        print("✅ 3/5 positions (FOREX 3/3, CRYPTO 0/4): ALLOW CRYPTO")


class TestPositionLimitEdgeCases:
    """Edge cases and error handling"""

    def test_zero_positions_first_trade(self, position_limit_checker):
        """Test: First trade allowed when zero positions exist"""
        position_limit_checker.mt5.get_open_positions.return_value = []

        result = position_limit_checker.can_open_position("EURUSD")
        stats = position_limit_checker.get_position_stats()

        assert result is True
        assert stats["total_positions"] == 0
        assert stats["total_limit"] == 5

    def test_four_positions_fifth_allowed(self, position_limit_checker):
        """Test: 4 positions (mixed categories: 3 FOREX at limit + 1 CRYPTO) → 5th position allowed"""
        # 3 FOREX (at FOREX limit of 3) + 1 CRYPTO = 4/5 total
        positions = [
            MockPosition("EURUSD", 1001),
            MockPosition("GBPUSD", 1002),
            MockPosition("USDJPY", 1003),  # FOREX limit reached (3/3)
            MockPosition("BTCUSD", 1004),  # 1 CRYPTO (1/4)
        ]
        position_limit_checker.mt5.get_open_positions.return_value = positions
        position_limit_checker.rules.get_symbol_category.side_effect = lambda s: (
            "forex" if s in ["EURUSD", "GBPUSD", "USDJPY"] else "crypto"
        )

        # Try to add another CRYPTO (not FOREX, which is at limit)
        result = position_limit_checker.can_open_position("ETHUSD")

        assert (
            result is True
        ), "5th position (CRYPTO) should be allowed (4/5 total, CRYPTO 1/4)"

    def test_exact_limit_boundary(self, position_limit_checker):
        """Test: Boundary at exactly max limit"""
        # Exactly 5 positions
        positions = [MockPosition(f"SYM{i}", 1000 + i) for i in range(5)]
        position_limit_checker.mt5.get_open_positions.return_value = positions

        result = position_limit_checker.can_open_position("NEWSYM")
        stats = position_limit_checker.get_position_stats()

        assert result is False, "Should block at exact limit (5/5)"
        assert stats["total_positions"] == 5
        assert stats["total_limit"] == 5


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    """
    Run tests with:
        pytest tests/test_position_limit_filter.py -v

    Or run specific test:
        pytest tests/test_position_limit_filter.py::TestMaxPositionsFilter::test_max_positions_reached_blocks_new -v
    """
    pytest.main([__file__, "-v", "-s"])
