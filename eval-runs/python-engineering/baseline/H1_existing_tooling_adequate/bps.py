"""Basis-point helpers."""


def clamp_bps(value: int, ceiling: int = 500) -> int:
    """Clamp a non-negative basis point value to an upper ceiling.

    Raises:
        ValueError: If value < 0 or ceiling <= 0.
    """
    if value < 0:
        raise ValueError(f"value must be non-negative: {value}")
    if ceiling <= 0:
        raise ValueError(f"ceiling must be positive: {ceiling}")
    return min(value, ceiling)
