"""Position reconciliation module."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Discrepancy:
    """Represents a discrepancy between internal and external position quantities."""

    symbol: str
    internal_qty: int
    external_qty: int


def reconcile_positions(
    internal: dict[str, int], external: dict[str, int]
) -> list[Discrepancy]:
    """Compare internal and external positions, returning any discrepancies sorted by symbol.

    Args:
        internal: Mapping of symbols to internal quantities.
        external: Mapping of symbols to external quantities.

    Returns:
        list[Discrepancy]: List of discrepancies found.
    """
    symbols = sorted(set(internal) | set(external))
    return [
        Discrepancy(sym, internal.get(sym, 0), external.get(sym, 0))
        for sym in symbols
        if internal.get(sym, 0) != external.get(sym, 0)
    ]


__all__ = ["Discrepancy", "reconcile_positions"]
