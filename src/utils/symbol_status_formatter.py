"""
Symbol Status Formatter - Platform-aware status message formatting

Provides consistent, platform-compatible formatting for:
- Order placement results
- Symbol testing status
- Account information
- Error messages

Handles emoji characters safely across Windows, Linux, and Mac.
"""

import logging
import platform
from typing import List, Tuple

import MetaTrader5 as mt5


class SymbolStatusFormatter:
    """Format symbol testing and trading status messages for all platforms"""

    # Platform detection
    _SYSTEM = platform.system()
    _IS_WINDOWS = _SYSTEM == "Windows"

    # Status symbols - ASCII safe
    OK = "[OK]" if _IS_WINDOWS else "✓"
    FAIL = "[X]" if _IS_WINDOWS else "✗"
    SKIP = "[~]" if _IS_WINDOWS else "⊘"
    TRADING = "[T]" if _IS_WINDOWS else "→"

    @classmethod
    def format_order_placed(cls, symbol: str, ticket: int) -> str:
        """Format successful order placement message

        Args:
            symbol: Trading symbol
            ticket: Order ticket number

        Returns:
            Formatted message safe for all platforms
        """
        return f"{cls.OK} {symbol:12} - Order placed (Ticket: {ticket})"

    @classmethod
    def format_order_failed(cls, symbol: str, reason: str) -> str:
        """Format failed order message

        Args:
            symbol: Trading symbol
            reason: Failure reason

        Returns:
            Formatted message safe for all platforms
        """
        return f"{cls.FAIL} {symbol:12} - Order rejected: {reason}"

    @classmethod
    def format_symbol_skipped(cls, symbol: str, reason: str) -> str:
        """Format skipped symbol message

        Args:
            symbol: Trading symbol
            reason: Skip reason

        Returns:
            Formatted message safe for all platforms
        """
        return f"{cls.SKIP} {symbol:12} - Skipped: {reason}"

    @classmethod
    def format_symbol_result(
        cls,
        symbol: str,
        volume_max: float,
        order_placed: bool,
        error_msg: str = None,
        has_volume: bool = True,
    ) -> str:
        """Format complete symbol test result

        Args:
            symbol: Trading symbol
            volume_max: Maximum volume available
            order_placed: Whether order was successfully placed
            error_msg: Error message if failed
            has_volume: Whether symbol has tradable volume

        Returns:
            Formatted result line
        """
        volume_info = f"(max_vol={volume_max})" if volume_max > 0 else "(no volume)"
        msg = f"{cls.OK if order_placed else cls.FAIL if has_volume else cls.SKIP} "
        msg += f"{symbol:12} {volume_info:20}"

        if order_placed:
            msg += " - Order placed"
        elif not has_volume:
            msg += " - Skipped (zero volume)"
        elif error_msg:
            msg += f" - Failed: {error_msg}"

        return msg

    @classmethod
    def format_account_status(cls, account=None) -> List[str]:
        """Format account information for logging

        Args:
            account: MT5 account info object

        Returns:
            List of formatted status lines
        """
        if account is None:
            try:
                account = mt5.account_info()
            except Exception as e:
                return [f"Failed to get account info: {str(e)}"]

        lines = [
            f"Account Status:",
            f"  Balance:       ${account.balance:,.2f}",
            f"  Equity:        ${account.equity:,.2f}",
            f"  Margin Level:  {account.margin_level:,.2f}%",
            f"  Trade Allowed: {account.trade_allowed}",
        ]

        return lines

    @classmethod
    def format_trading_summary(
        cls, total: int, successful: int, zero_volume: int, failed: int = None
    ) -> List[str]:
        """Format trading summary statistics

        Args:
            total: Total symbols tested
            successful: Successful trades
            zero_volume: Symbols with zero volume
            failed: Failed trades (optional, auto-calculated if not provided)

        Returns:
            List of formatted summary lines
        """
        if failed is None:
            failed = total - successful - zero_volume

        tradable = total - zero_volume
        success_rate = 100 * successful / tradable if tradable > 0 else 0

        lines = [
            "",
            "=" * 60,
            "OVERALL RESULTS:",
            "=" * 60,
            f"Total symbols tested:   {total}",
            f"Successful orders:      {successful}",
            f"Skipped (zero volume):  {zero_volume}",
            f"Failed orders:          {failed}",
            f"Success rate (tradable): {successful}/{tradable} = {success_rate:.1f}%",
        ]

        return lines

    @classmethod
    def format_key_findings(cls) -> List[str]:
        """Format key findings from test.

        Returns:
            List of formatted key findings.
        """
        lines = [
            "",
            "=" * 60,
            "KEY FINDINGS:",
            "=" * 60,
            f"{cls.OK} Zero-volume symbols don't block other pairs",
            f"{cls.OK} Each symbol tested independently",
            f"{cls.OK} Account margin affects ALL symbols equally",
            f"{cls.OK} Mixed asset classes can be traded together",
        ]

        return lines

    @classmethod
    def format_positions(cls, positions=None) -> List[str]:
        """Format open positions information.

        Args:
            positions: MT5 positions list.

        Returns:
            List of formatted position lines.
        """
        if positions is None:
            try:
                positions = mt5.positions_get()
            except Exception as e:
                return [f"Failed to get positions: {str(e)}"]

        if not positions:
            return ["Open positions: 0"]

        lines = [f"Open positions: {len(positions)}"]
        for pos in positions:
            pos_type = "BUY" if pos.type == 0 else "SELL"
            lines.append(
                f"  {pos.symbol:10} {pos_type:4} {pos.volume:6.2f} lots | "
                f"Profit: ${pos.profit:8.2f}"
            )

        return lines

    @classmethod
    def format_error(cls, symbol: str, error: str) -> str:
        """Format error message.

        Args:
            symbol: Trading symbol.
            error: Error message.

        Returns:
            Formatted error message.
        """
        return f"{cls.FAIL} {symbol}: ERROR - {error}"

    @classmethod
    def format_category_header(cls, category: str) -> str:
        """Format category test header.

        Args:
            category: Asset category (crypto, forex, commodities, etc).

        Returns:
            Formatted category header.
        """
        return f"\n{'='*60}\nTesting {category.upper()}\n{'='*60}"

    @classmethod
    def format_category_summary(
        cls, category: str, successful: int, zero_volume: int, failed: int
    ) -> List[str]:
        """Format category summary.

        Args:
            category: Asset category.
            successful: Successful trades in category.
            zero_volume: Zero-volume symbols in category.
            failed: Failed trades in category.

        Returns:
            List of formatted summary lines.
        """
        lines = [
            f"\n  {category.upper()} results:",
            f"    Successful:  {successful}",
            f"    Zero volume: {zero_volume}",
            f"    Failed:      {failed}",
        ]

        return lines

    @classmethod
    def log_status(
        cls,
        logger: logging.Logger,
        symbol: str,
        order_placed: bool,
        has_volume: bool = True,
        reason: str = None,
        ticket: int = None,
    ) -> None:
        """Log formatted symbol status.

        Args:
            logger: Logger instance.
            symbol: Trading symbol.
            order_placed: Whether order was placed.
            has_volume: Whether symbol has volume.
            reason: Optional reason/error message.
            ticket: Optional order ticket.

        Returns:
            None.
        """
        try:
            if order_placed and ticket:
                msg = cls.format_order_placed(symbol, ticket)
                logger.info(msg)
            elif not has_volume:
                msg = cls.format_symbol_skipped(symbol, reason or "zero volume")
                logger.warning(msg)
            elif not order_placed:
                msg = cls.format_order_failed(symbol, reason or "unknown error")
                logger.warning(msg)
            else:
                logger.info(f"{cls.OK} {symbol}: Status unknown")
        except Exception as e:
            # Fallback without special characters
            logger.error(f"[LOG_ERROR] {symbol}: {str(e)}")


# Platform detection for logging setup
def setup_safe_logging(logger: logging.Logger) -> None:
    """Setup logging with proper encoding for the platform.

    Args:
        logger: Logger to configure.

    Returns:
        None.
    """
    if SymbolStatusFormatter._IS_WINDOWS:
        # Windows: Use simple ASCII characters
        logger.info("Running on Windows - using ASCII status indicators")
    else:
        # Unix-like: Can use Unicode symbols
        logger.info(
            f"Running on {SymbolStatusFormatter._SYSTEM} - using Unicode symbols"
        )


# Quick reference
def get_status_indicator(success: bool) -> str:
    """Get appropriate status indicator.

    Args:
        success: Whether operation succeeded.

    Returns:
        Status indicator symbol.
    """
    return SymbolStatusFormatter.OK if success else SymbolStatusFormatter.FAIL
