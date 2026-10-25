"""Account ledger and position booking core."""

# Re-exported for backward compatibility with legacy callers
from ledger.reconciliation import Discrepancy, reconcile_positions


class AccountLedger:
    """Position booking ledger."""

    def __init__(self) -> None:
        self._positions: dict[str, int] = {}

    def book(self, symbol: str, delta: int) -> None:
        """Book a position change."""
        self._positions[symbol] = self._positions.get(symbol, 0) + delta

    def snapshot(self) -> dict[str, int]:
        """Return a snapshot of all positions."""
        return dict(self._positions)


__all__ = ["AccountLedger", "Discrepancy", "reconcile_positions"]
