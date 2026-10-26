"""Position netting module."""

from collections import defaultdict


def net_positions(trades: list[tuple[str, int]]) -> dict[str, int]:
    """Aggregate trade quantities by symbol and return non-zero net positions."""
    totals: defaultdict[str, int] = defaultdict(int)
    for sym, qty in trades:
        totals[sym] += qty
    return {sym: total for sym, total in totals.items() if total != 0}
