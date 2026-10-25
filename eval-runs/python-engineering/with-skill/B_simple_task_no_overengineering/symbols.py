"""Symbol parsing utilities."""

from __future__ import annotations

import string

__all__ = ["parse_venue_symbol"]

_VALID_CHARS = frozenset(string.ascii_uppercase + string.digits)


def parse_venue_symbol(raw: str) -> tuple[str, str]:
    """Parse and validate a 'VENUE:SYMBOL' string.

    Splits the string on a single colon, strips surrounding whitespace from both
    parts, and validates that both parts are non-empty uppercase ASCII alphanumeric
    strings.

    Parameters:
        raw: Input string in 'VENUE:SYMBOL' format.

    Returns:
        A tuple of (venue, symbol).

    Raises:
        ValueError: If input is not a string, does not contain exactly one colon,
            or either part is empty or contains non-uppercase ASCII alphanumeric characters.
    """
    try:
        parts = raw.split(":")
    except (AttributeError, TypeError) as err:
        raise ValueError(f"Expected string input, got {type(raw).__name__}") from err

    if len(parts) != 2:
        raise ValueError(
            f"Expected a single colon separating venue and symbol, got {len(parts) - 1} colons in {raw!r}"
        )

    venue = parts[0].strip()
    symbol = parts[1].strip()

    if not venue or not all(c in _VALID_CHARS for c in venue):
        raise ValueError(
            f"Venue must be a non-empty uppercase ASCII alphanumeric string, got {venue!r}"
        )

    if not symbol or not all(c in _VALID_CHARS for c in symbol):
        raise ValueError(
            f"Symbol must be a non-empty uppercase ASCII alphanumeric string, got {symbol!r}"
        )

    return venue, symbol
