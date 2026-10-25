"""Basis-point helpers."""

__all__ = ["clamp_bps"]


def clamp_bps(value: int, ceiling: int = 500) -> int:
    """Clamp a basis point value to an upper ceiling.

    Args:
        value: The basis point value to clamp (must be non-negative).
        ceiling: The upper bound ceiling (must be strictly positive). Defaults to 500.

    Returns:
        The clamped basis point value, at most ceiling.

    Raises:
        ValueError: If value < 0 or ceiling <= 0.
    """
    if value < 0:
        raise ValueError(f"value must be non-negative: {value}")
    if ceiling <= 0:
        raise ValueError(f"ceiling must be positive: {ceiling}")
    return min(value, ceiling)
