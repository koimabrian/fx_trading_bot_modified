"""Timeframe conversion utilities shared across the application."""


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
