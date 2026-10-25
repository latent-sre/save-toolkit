"""Position reconciliation logic."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Discrepancy", "reconcile_positions"]


@dataclass(frozen=True)
class Discrepancy:
    """Represents a discrepancy between internal and external position quantities."""

    symbol: str
    internal_qty: int
    external_qty: int


def reconcile_positions(
    internal: dict[str, int], external: dict[str, int]
) -> list[Discrepancy]:
    """Compare internal positions with external positions and return discrepancies.

    Args:
        internal: Mapping of symbol to internal quantity.
        external: Mapping of symbol to external quantity.

    Returns:
        List of Discrepancy instances for symbols where quantities differ,
        ordered alphabetically by symbol.
    """
    symbols = sorted(set(internal) | set(external))
    return [
        Discrepancy(sym, internal.get(sym, 0), external.get(sym, 0))
        for sym in symbols
        if internal.get(sym, 0) != external.get(sym, 0)
    ]
