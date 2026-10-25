"""Basis-point helpers."""


def clamp_bps(value: int, ceiling: int = 500) -> int:
    """Clamp a non-negative basis-point value to a strictly positive ceiling.

    Args:
        value: The basis point value (must be >= 0).
        ceiling: The upper bound basis point limit (must be > 0, default 500).

    Returns:
        The clamped basis point integer, min(value, ceiling).

    Raises:
        ValueError: If value < 0 or ceiling <= 0.
    """
    if value < 0:
        raise ValueError(f"Basis-point value must be non-negative, got {value}")
    if ceiling <= 0:
        raise ValueError(f"Ceiling must be strictly positive, got {ceiling}")
    return min(value, ceiling)
