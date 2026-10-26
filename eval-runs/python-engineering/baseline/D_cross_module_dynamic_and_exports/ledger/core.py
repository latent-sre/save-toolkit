"""Core account ledger implementation."""

from __future__ import annotations

# Re-export reconciliation symbols for backward compatibility
from ledger.reconciliation import Discrepancy, reconcile_positions


class AccountLedger:
    """In-memory account ledger tracking positions per symbol."""

    def __init__(self) -> None:
        self._positions: dict[str, int] = {}

    def book(self, symbol: str, delta: int) -> None:
        """Book a quantity delta for a symbol."""
        self._positions[symbol] = self._positions.get(symbol, 0) + delta

    def snapshot(self) -> dict[str, int]:
        """Return a copy of the current position snapshot."""
        return dict(self._positions)


__all__ = ["AccountLedger", "Discrepancy", "reconcile_positions"]
