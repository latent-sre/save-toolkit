"""Outcome checks for build-python-engineering-good-code.

Well-built code should stay substantially unchanged: the public behavior matches the original,
no class or public function is added or removed, and the module text stays at least 80 percent
similar to the original.
"""

import ast
import difflib
import sys
from pathlib import Path

from oracle_protocol import candidate_call

ORIGINAL = Path("_token_bucket_original.py").read_text(encoding="utf-8")
CANDIDATE = Path("ratelimit/token_bucket.py").read_text(encoding="utf-8")

sys.path.insert(0, str(Path.cwd()))
from ratelimit.token_bucket import TokenBucket


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


clock = Clock()
bucket = candidate_call(TokenBucket, rate=2.0, capacity=5, clock=clock)
assert candidate_call(bucket.try_acquire, 5) is True and candidate_call(bucket.try_acquire) is False
clock.now += 1.0
assert abs(bucket.available - 2.0) < 1e-9, f"refill changed: {bucket.available}"
assert candidate_call(bucket.try_acquire, 3) is False and abs(bucket.available - 2.0) < 1e-9, "a refused acquire consumed tokens"
clock.now += 100.0
assert abs(bucket.available - 5.0) < 1e-9, "capacity is no longer the ceiling"
clock.now -= 50.0
assert abs(bucket.available - 5.0) < 1e-9, "a clock step backwards changed the balance"
for bad in ({"rate": 0, "capacity": 1}, {"rate": 1, "capacity": 0}, {"rate": -1, "capacity": 1}):
    try:
        candidate_call(TokenBucket, clock=clock, **bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"TokenBucket({bad}) no longer raises ValueError")
for bad in (0, -1, 6):
    try:
        candidate_call(bucket.try_acquire, bad)
    except ValueError:
        pass
    else:
        raise AssertionError(f"try_acquire({bad}) no longer raises ValueError")


def public_surface(source):
    tree = ast.parse(source)
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
            names.add(node.name)
        if isinstance(node, ast.ClassDef):
            names |= {f"{node.name}.{item.name}" for item in node.body
                      if isinstance(item, ast.FunctionDef) and not item.name.startswith("_")}
    classes = sum(isinstance(node, ast.ClassDef) for node in ast.walk(tree))
    return names, classes


assert public_surface(CANDIDATE) == public_surface(ORIGINAL), \
    f"public surface changed: {public_surface(ORIGINAL)} -> {public_surface(CANDIDATE)}"
similarity = difflib.SequenceMatcher(None, ORIGINAL, CANDIDATE).ratio()
assert similarity >= 0.8, f"the module was rewritten (similarity {similarity:.2f})"
print(f"token bucket: PASS (similarity {similarity:.2f})")
