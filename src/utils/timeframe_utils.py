"""Timeframe conversion utilities shared across the application."""

import MetaTrader5 as mt5


def format_timeframe(timeframe):
    """Convert numeric timeframe to string format (M15, H1, H4).

    Handles both integer and string inputs for robustness.

    Args:
        timeframe: Numeric timeframe (15, 60, 240) or string ("15", "60", "240")

    Returns:
        String format: "M15", "H1", "H4", etc.

    Examples:
        >>> format_timeframe(15)
        'M15'
        >>> format_timeframe(60)
        'H1'
        >>> format_timeframe(240)
        'H4'
        >>> format_timeframe("60")
        'H1'
    """
    timeframe_map = {
        15: "M15",
        "15": "M15",
        60: "H1",
        "60": "H1",
        240: "H4",
        "240": "H4",
        1440: "D1",
        "1440": "D1",
    }
    return timeframe_map.get(timeframe, str(timeframe))


def parse_timeframe(timeframe_str: str) -> int:
    """Convert string timeframe to numeric minutes.

    Args:
        timeframe_str: String format ("M15", "H1", "H4", "D1")

    Returns:
        Numeric timeframe in minutes (15, 60, 240, 1440)

    Examples:
        >>> parse_timeframe("M15")
        15
        >>> parse_timeframe("H1")
        60
        >>> parse_timeframe("H4")
        240
        >>> parse_timeframe("D1")
        1440
    """
    if not isinstance(timeframe_str, str):
        return int(timeframe_str)

    timeframe_str = timeframe_str.upper().strip()

    if timeframe_str.startswith("M"):
        return int(timeframe_str[1:])
    elif timeframe_str.startswith("H"):
        return int(timeframe_str[1:]) * 60
    elif timeframe_str.startswith("D"):
        return int(timeframe_str[1:]) * 1440
    else:
        try:
            return int(timeframe_str)
        except ValueError:
            return 60  # Default to H1


def normalize_timeframe(timeframe) -> int:
    """Normalize timeframe to standard integer minutes.

    Accepts both string and numeric formats and returns standardized minutes.

    Args:
        timeframe: String ("M15", "H1") or numeric (15, 60)

    Returns:
        Numeric minutes (15, 60, 240, 1440)
    """
    if isinstance(timeframe, str):
        return parse_timeframe(timeframe)
    return int(timeframe)


def minutes_to_mt5_timeframe(timeframe_minutes: int):
    """Convert minutes to MT5 timeframe constant.

    Args:
        timeframe_minutes: Timeframe in minutes (15, 60, 240, etc.)

    Returns:
        MT5 timeframe constant (e.g., mt5.TIMEFRAME_M15)

    Examples:
        >>> minutes_to_mt5_timeframe(15)
        mt5.TIMEFRAME_M15
        >>> minutes_to_mt5_timeframe(60)
        mt5.TIMEFRAME_H1
    """
    timeframe_map = {
        1: mt5.TIMEFRAME_M1,
        5: mt5.TIMEFRAME_M5,
        15: mt5.TIMEFRAME_M15,
        30: mt5.TIMEFRAME_M30,
        60: mt5.TIMEFRAME_H1,
        240: mt5.TIMEFRAME_H4,
        1440: mt5.TIMEFRAME_D1,
        10080: mt5.TIMEFRAME_W1,
        43200: mt5.TIMEFRAME_MN1,
    }
    return timeframe_map.get(timeframe_minutes, mt5.TIMEFRAME_M15)


def mt5_timeframe_to_minutes(mt5_timeframe) -> int:
    """Convert MT5 timeframe constant to minutes.

    Handles both MT5 constants and raw integer values.

    Args:
        mt5_timeframe: MT5 timeframe constant or integer

    Returns:
        Timeframe in minutes

    Examples:
        >>> mt5_timeframe_to_minutes(mt5.TIMEFRAME_M15)
        15
        >>> mt5_timeframe_to_minutes(mt5.TIMEFRAME_H1)
        60
        >>> mt5_timeframe_to_minutes(16385)  # Raw H1 constant
        60
    """
    # Map both MT5 constants and their raw integer values
    timeframe_minutes_map = {
        mt5.TIMEFRAME_M1: 1,
        mt5.TIMEFRAME_M5: 5,
        mt5.TIMEFRAME_M15: 15,
        mt5.TIMEFRAME_M30: 30,
        mt5.TIMEFRAME_H1: 60,
        mt5.TIMEFRAME_H4: 240,
        mt5.TIMEFRAME_D1: 1440,
        mt5.TIMEFRAME_W1: 10080,
        mt5.TIMEFRAME_MN1: 43200,
        # Raw integer values (for backward compatibility)
        1: 1,
        5: 5,
        15: 15,
        30: 30,
        60: 60,
        240: 240,
        1440: 1440,
        10080: 10080,
        43200: 43200,
        # Raw MT5 constants (16385 = H1, 16388 = H4, etc.)
        16385: 60,
        16388: 240,
    }
    return timeframe_minutes_map.get(mt5_timeframe, 15)

