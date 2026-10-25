"""Symbol parsing utilities."""

import string

_VALID_CHARS = frozenset(string.ascii_uppercase + string.digits)


def parse_venue_symbol(raw: str) -> tuple[str, str]:
    """Split a 'VENUE:SYMBOL' string and validate both parts.

    Splits on a single colon, strips surrounding whitespace, and validates that
    both parts are non-empty uppercase ASCII alphanumeric strings.

    Args:
        raw: Input string in 'VENUE:SYMBOL' format.

    Returns:
        A tuple of (venue, symbol).

    Raises:
        ValueError: If raw is not a string, does not contain exactly one colon,
            or either part fails the validation criteria.
    """
    try:
        parts = raw.split(":")
    except (AttributeError, TypeError) as err:
        raise ValueError("raw must be a string") from err

    if len(parts) != 2:
        raise ValueError(f"Expected exactly one colon in venue symbol string: {raw!r}")

    venue = parts[0].strip()
    symbol = parts[1].strip()

    if not venue or not _VALID_CHARS.issuperset(venue):
        raise ValueError(
            f"Invalid venue {venue!r}: must be non-empty uppercase ASCII alphanumeric"
        )

    if not symbol or not _VALID_CHARS.issuperset(symbol):
        raise ValueError(
            f"Invalid symbol {symbol!r}: must be non-empty uppercase ASCII alphanumeric"
        )

    return venue, symbol
