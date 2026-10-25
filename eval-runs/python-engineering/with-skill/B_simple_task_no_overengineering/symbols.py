"""Symbol parsing and validation utilities."""

from __future__ import annotations

__all__ = ["parse_venue_symbol"]


def _is_uppercase_ascii_alnum(value: str) -> bool:
    """Return True if value is a non-empty uppercase ASCII alphanumeric string."""
    return bool(value) and value.isascii() and value.isalnum() and value.isupper()


def parse_venue_symbol(raw: str) -> tuple[str, str]:
    """Parse a venue-qualified symbol of the form `'VENUE:SYMBOL'`.

    Splits on a single colon, strips surrounding whitespace from both parts,
    and validates that both venue and symbol are non-empty uppercase ASCII
    alphanumeric strings.

    Args:
        raw: Input string formatted as `'VENUE:SYMBOL'`.

    Returns:
        A tuple of `(venue, symbol)`.

    Raises:
        ValueError: If `raw` does not contain exactly one colon, or either part
            fails the non-empty uppercase ASCII alphanumeric validation.
    """
    try:
        parts = raw.split(":")
    except AttributeError as err:
        raise ValueError(f"Input must be a string, got {type(raw).__name__}") from err

    if len(parts) != 2:
        raise ValueError(
            f"Invalid venue symbol format, expected exactly one colon separator: {raw!r}"
        )

    venue = parts[0].strip()
    symbol = parts[1].strip()

    if not _is_uppercase_ascii_alnum(venue):
        raise ValueError(
            f"Venue must be a non-empty uppercase ASCII alphanumeric string, got: {venue!r}"
        )

    if not _is_uppercase_ascii_alnum(symbol):
        raise ValueError(
            f"Symbol must be a non-empty uppercase ASCII alphanumeric string, got: {symbol!r}"
        )

    return venue, symbol
