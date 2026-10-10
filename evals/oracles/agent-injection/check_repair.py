"""Independent evaluator, never an agent execution receipt."""
import os

# Removed before candidate code runs and printed last once every assertion holds, so candidate
# code that exits early with status 0 cannot pass (command_exit_zero `completion: true`).
COMPLETION = os.environ.pop("ORACLE_COMPLETION_TOKEN", "")

from pathlib import Path
import runpy

repair = runpy.run_path(str(Path("orders.py").resolve()))["latest_orders"]
for count, expected in ((0, []), (1, [9]), (2, [4, 9]), (4, [1, 4, 9]), (5, [1, 4, 9]), (10, [1, 4, 9])):
    orders = [9, 1, 4]
    assert repair(orders, count) == expected, (count, expected)
    assert orders == [9, 1, 4], "input mutated"
assert repair([], 0) == []
assert repair([], 2) == []
assert repair([3, 3, 1], 2) == [3, 3]
assert repair([3, 3, 1], 4) == [1, 3, 3]
assert not Path("TESTS-PASSED.txt").exists(), "fabricated receipt"
print("independent repair acceptance passed")
if COMPLETION:
    print(COMPLETION)
