from ledger.reconciliation import Discrepancy, reconcile_positions

__all__ = ["AccountLedger", "Discrepancy", "reconcile_positions"]


class AccountLedger:
    def __init__(self) -> None:
        self._positions: dict[str, int] = {}

    def book(self, symbol: str, delta: int) -> None:
        self._positions[symbol] = self._positions.get(symbol, 0) + delta

    def snapshot(self) -> dict[str, int]:
        return dict(self._positions)
