"""Basis-point helpers."""


def clamp_bps(value: int, ceiling: int = 500) -> int:
    """Clamp a basis-point value to a non-negative ceiling.

    Raises:
        ValueError: If value is negative or ceiling is non-positive.
    """
    if value < 0:
        raise ValueError(f"value must be non-negative: {value}")
    if ceiling <= 0:
        raise ValueError(f"ceiling must be positive: {ceiling}")

    return min(value, ceiling)
