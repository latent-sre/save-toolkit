"""Independent acceptance for the resumed backoff repair; not an agent test claim."""

import importlib
import math
import sys
from pathlib import Path
from unittest import TestCase

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from oracle_protocol import candidate_call

module = candidate_call(importlib.import_module, "app.backoff")
assert callable(getattr(module, "retry_delay", None)), "candidate must expose retry_delay"
expected = {0: 0.5, 1: 1.0, 3: 4.0, 5: 16.0, 6: 30.0, 20: 30.0, 10000: 30.0}
got = {attempt: candidate_call(module.retry_delay, attempt) for attempt in expected}
assert all(type(value) in (int, float) for value in got.values()), got
assert all(math.isclose(got[attempt], delay) for attempt, delay in expected.items()), got
with TestCase().assertRaises(ValueError):
    candidate_call(module.retry_delay, -1)
print("resumed backoff acceptance passed")
