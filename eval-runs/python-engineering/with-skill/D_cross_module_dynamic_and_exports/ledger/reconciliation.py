from dataclasses import dataclass

__all__ = ["Discrepancy", "reconcile_positions"]


@dataclass(frozen=True)
class Discrepancy:
    symbol: str
    internal_qty: int
    external_qty: int


def reconcile_positions(
    internal: dict[str, int], external: dict[str, int]
) -> list[Discrepancy]:
    symbols = sorted(set(internal) | set(external))
    return [
        Discrepancy(sym, internal.get(sym, 0), external.get(sym, 0))
        for sym in symbols
        if internal.get(sym, 0) != external.get(sym, 0)
    ]
