"""Core account ledger and position booking."""

from __future__ import annotations

# Re-export reconciliation symbols for backward compatibility with callers and dynamic plugin hooks
from ledger.reconciliation import Discrepancy, reconcile_positions

__all__ = ["AccountLedger", "Discrepancy", "reconcile_positions"]


class AccountLedger:
    """Manages internal position booking."""

    def __init__(self) -> None:
        self._positions: dict[str, int] = {}

    def book(self, symbol: str, delta: int) -> None:
        self._positions[symbol] = self._positions.get(symbol, 0) + delta

    def snapshot(self) -> dict[str, int]:
        return dict(self._positions)
