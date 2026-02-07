"""
Symbol Tester Base - Reusable base class for symbol testing

Provides common functionality for testing trading on different symbols:
- Symbol info retrieval and validation
- Order placement attempts
- Result tracking
- Summary reporting

Designed to be extended by specific test classes (MixedAsset, MajorPairs, etc)
following the DRY principle.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import MetaTrader5 as mt5

from src.database.db_manager import DatabaseManager
from src.core.mt5_connector import MT5Connector
from src.utils.config_manager import ConfigManager
from src.utils.logging_factory import LoggingFactory
from src.utils.symbol_status_formatter import SymbolStatusFormatter


@dataclass
class SymbolTestResult:
    """Result of testing a single symbol"""

    symbol: str
    category: str
    has_volume: bool
    volume_max: float
    order_placed: bool
    deal_id: int = None
    error_msg: str = None
    order_id: int = None
    ticket: int = None


@dataclass
class TestSummary:
    """Summary of test results"""

    total_tested: int = 0
    total_successful: int = 0
    total_zero_volume: int = 0
    total_failed: int = 0
    category_results: Dict[str, List[SymbolTestResult]] = field(default_factory=dict)

    @property
    def tradable_count(self) -> int:
        """Number of symbols with tradable volume"""
        return self.total_tested - self.total_zero_volume

    @property
    def success_rate(self) -> float:
        """Success rate percentage (tradable symbols only)"""
        if self.tradable_count == 0:
            return 0.0
        return 100 * self.total_successful / self.tradable_count


class SymbolTesterBase(ABC):
    """Base class for symbol testing

    Provides common methods for:
    - Symbol info retrieval
    - Volume validation
    - Order placement
    - Result tracking

    Extend this class to create specific test scenarios.
    """

    MIN_VOLUME_THRESHOLD = 0.001  # Minimum volume to consider trading

    def __init__(self, config_path: str = "src/config/config.yaml"):
        """Initialize tester with configuration

        Args:
            config_path: Path to config.yaml file
        """
        self.logger = LoggingFactory.get_logger(__name__)
        self.config_path = config_path
        self.config = None
        self.db = None
        self.mt5_connector = None
        self.results: Dict[str, SymbolTestResult] = {}

    def load_config(self) -> bool:
        """Load configuration from YAML file.

        Returns:
            True if successful, False otherwise.
        """
        try:
            self.config = ConfigManager.get_config()
            self.logger.debug(f"Configuration loaded from config manager")
            return True
        except Exception as e:
            self.logger.error(f"Failed to load config: {str(e)}")
            return False

    def initialize(self) -> bool:
        """Initialize MT5 connection.

        Returns:
            True if successful, False otherwise.
        """
        if not self.load_config():
            return False

        try:
            self.db = DatabaseManager(self.config["database"])
            self.db.connect()
            self.logger.debug("Database connected")

            self.mt5_connector = MT5Connector(self.config["mt5"])
            if not self.mt5_connector.initialize():
                self.logger.error("Failed to initialize MT5")
                return False

            self.logger.info("MT5 initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Initialization failed: {str(e)}")
            return False

    def get_symbol_info(self, symbol: str) -> Tuple[bool, float, str]:
        """Get symbol information and validate trading capability.

        Args:
            symbol: Trading symbol to check.

        Returns:
            Tuple of (has_volume: bool, volume_max: float, error_msg: str or None).
        """
        try:
            info = mt5.symbol_info(symbol)
            if not info:
                return False, 0, f"Symbol not found in MT5"

            volume_max = info.volume_max
            has_tradable_volume = volume_max >= self.MIN_VOLUME_THRESHOLD

            if not has_tradable_volume:
                return False, volume_max, f"Zero/minimal volume (max={volume_max})"

            return True, volume_max, None
        except Exception as e:
            return False, 0, f"Exception: {str(e)}"

    def attempt_trade(self, symbol: str, category: str) -> SymbolTestResult:
        """Attempt to place a trade on a symbol.

        Args:
            symbol: Trading symbol.
            category: Asset category (crypto, forex, etc).

        Returns:
            SymbolTestResult with outcome.
        """
        self.logger.info(f"[Testing {category}] {symbol}...")

        # Check symbol has tradable volume
        has_volume, volume_max, error = self.get_symbol_info(symbol)

        result = SymbolTestResult(
            symbol=symbol,
            category=category,
            has_volume=has_volume,
            volume_max=volume_max,
            order_placed=False,
            error_msg=error,
        )

        # If symbol has no volume, skip with explanation
        if not has_volume:
            self.logger.warning(
                f"  {SymbolStatusFormatter.SKIP} {symbol}: Skipping - {error}"
            )
            return result

        # Try to place order
        try:
            signal = {"symbol": symbol, "action": "buy", "volume": 0.01}

            success = self.mt5_connector.place_order(signal, "symbol_test")

            if success:
                # Get the position to extract deal ID
                positions = mt5.positions_get(symbol=symbol)
                if positions:
                    pos = positions[-1]
                    result.order_placed = True
                    result.deal_id = pos.ticket
                    result.ticket = pos.ticket
                    result.order_id = pos.ticket

                    msg = SymbolStatusFormatter.format_order_placed(symbol, pos.ticket)
                    self.logger.info(f"  {msg}")
            else:
                result.error_msg = "Order placement failed"
                msg = SymbolStatusFormatter.format_order_failed(
                    symbol, result.error_msg
                )
                self.logger.warning(f"  {msg}")

        except Exception as e:
            result.error_msg = f"Exception during placement: {str(e)}"
            msg = SymbolStatusFormatter.format_error(symbol, result.error_msg)
            self.logger.error(f"  {msg}")

        return result

    def get_account_status(self) -> Dict:
        """Get current account information.

        Returns:
            Dictionary with account details.
        """
        try:
            account = mt5.account_info()
            return {
                "balance": account.balance,
                "equity": account.equity,
                "margin_level": account.margin_level,
                "trade_allowed": account.trade_allowed,
            }
        except Exception as e:
            self.logger.error(f"Failed to get account info: {str(e)}")
            return {}

    def log_account_status(self) -> None:
        """Log current account status.

        Returns:
            None.
        """
        account = mt5.account_info()
        for line in SymbolStatusFormatter.format_account_status(account):
            self.logger.info(line)

    @abstractmethod
    def run_tests(self) -> TestSummary:
        """Run the test suite.

        Must be implemented by subclasses.

        Returns:
            TestSummary with results.
        """
        pass

    def print_summary(self, summary: TestSummary) -> None:
        """Print test summary.

        Args:
            summary: TestSummary object with results.

        Returns:
            None.
        """
        self.logger.info("=" * 60)
        self.logger.info("TEST SUMMARY")
        self.logger.info("=" * 60)

        for line in SymbolStatusFormatter.format_trading_summary(
            total=summary.total_tested,
            successful=summary.total_successful,
            zero_volume=summary.total_zero_volume,
            failed=summary.total_failed,
        ):
            self.logger.info(line)

        # Key findings
        for line in SymbolStatusFormatter.format_key_findings():
            self.logger.info(line)

        # Positions
        for line in SymbolStatusFormatter.format_positions():
            self.logger.info(line)

    def cleanup(self) -> None:
        """Clean up resources.

        Returns:
            None.
        """
        try:
            if self.db:
                self.db.close()
            # MT5 connector doesn't have shutdown, just close connection
            if self.mt5_connector and hasattr(self.mt5_connector, "shutdown"):
                self.mt5_connector.shutdown()
            self.logger.debug("Cleanup completed")
        except Exception as e:
            self.logger.error(f"Cleanup error: {str(e)}")

    def run_and_cleanup(self) -> TestSummary:
        """Run tests with automatic cleanup.

        Returns:
            TestSummary with results.
        """
        try:
            return self.run_tests()
        finally:
            self.cleanup()
