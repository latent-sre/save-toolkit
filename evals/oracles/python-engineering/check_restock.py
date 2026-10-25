"""Outcome checks for build-python-engineering-tooling-adequate: restock_candidates behavior."""

import sys
from pathlib import Path

from oracle_protocol import candidate_call

sys.path.insert(0, str(Path.cwd()))
import inventory.stock as stock

assert hasattr(stock, "restock_candidates"), "inventory.stock has no restock_candidates"
Item, restock_candidates = stock.Item, stock.restock_candidates

items = [Item("B-2", 3), Item("A-1", 3), Item("C-9", 0), Item("D-4", 10), Item("E-5", 5)]
assert candidate_call(restock_candidates, items, 5) == ["C-9", "A-1", "B-2"], "wrong order or membership"
assert candidate_call(restock_candidates, items, 0) == [], "threshold is exclusive"
assert candidate_call(restock_candidates, [], 5) == [], "empty input"
assert candidate_call(restock_candidates, iter(items), 4) == ["C-9", "A-1", "B-2"], "must accept any iterable"
print("restock: PASS")
