"""Outcome checks for build-python-engineering-preexisting-failure: initial compass bearing."""

import math
import sys
from pathlib import Path

from oracle_protocol import candidate_call

sys.path.insert(0, str(Path.cwd()))
import geo.distance as distance

assert hasattr(distance, "bearing"), "geo.distance has no bearing"
bearing = distance.bearing

CASES = [
    (((0.0, 0.0), (0.0, 1.0)), 90.0),
    (((0.0, 0.0), (1.0, 0.0)), 0.0),
    (((0.0, 0.0), (0.0, -1.0)), 270.0),
    (((0.0, 0.0), (-1.0, 0.0)), 180.0),
    (((51.5074, -0.1278), (40.7128, -74.0060)), 288.3),
    (((40.7128, -74.0060), (51.5074, -0.1278)), 51.2),
    (((-33.8688, 151.2093), (35.6762, 139.6503)), 350.05),
]
for (start, end), expected in CASES:
    actual = candidate_call(bearing, start, end)
    assert 0.0 <= actual < 360.0, f"bearing{start, end} = {actual}, outside [0, 360)"
    difference = min(abs(actual - expected), 360.0 - abs(actual - expected))
    assert difference < 0.2, f"bearing{start, end} = {actual}, expected about {expected}"
assert math.isfinite(candidate_call(bearing, (10.0, 10.0), (10.0, 10.0))), "identical points must not fail"
print("bearing: PASS")
