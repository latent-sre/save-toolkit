"""Symbol and identifier parsing utilities."""

from __future__ import annotations

import re

_UPPER_ALPHANUMERIC = re.compile(r"^[A-Z0-9]+$")


def _is_uppercase_alnum(value: str) -> bool:
    """Return True if value consists solely of uppercase ASCII alphanumeric characters."""
    return bool(_UPPER_ALPHANUMERIC.match(value))


def parse_venue_symbol(raw: str) -> tuple[str, str]:
    """Parse and validate a 'VENUE:SYMBOL' asset identifier string.

    Splits the string on a single colon, strips surrounding whitespace from both parts,
    and validates that each component is a non-empty uppercase ASCII alphanumeric string.

    Args:
        raw: The raw input string formatted as 'VENUE:SYMBOL'.

    Returns:
        tuple[str, str]: A pair of (venue, symbol).

    Raises:
        ValueError: If raw is not a string, does not contain exactly one colon,
            or either part fails validation.
    """
    if not isinstance(raw, str):
        raise ValueError(f"Expected string input, got {type(raw).__name__}")  # noqa: TRY004

    if raw.count(":") != 1:
        raise ValueError(f"Input must contain exactly one colon delimiter, got: {raw!r}")

    venue_raw, symbol_raw = raw.split(":", 1)
    venue = venue_raw.strip()
    symbol = symbol_raw.strip()

    if not venue:
        raise ValueError(f"Venue component cannot be empty: {raw!r}")
    if not symbol:
        raise ValueError(f"Symbol component cannot be empty: {raw!r}")

    if not _is_uppercase_alnum(venue):
        raise ValueError(
            f"Venue {venue!r} must be a non-empty uppercase ASCII alphanumeric string"
        )
    if not _is_uppercase_alnum(symbol):
        raise ValueError(
            f"Symbol {symbol!r} must be a non-empty uppercase ASCII alphanumeric string"
        )

    return venue, symbol


__all__ = ["parse_venue_symbol"]
