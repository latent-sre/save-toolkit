"""Outcome checks for build-python-engineering-replace-dependency.

The original dateutil implementation is the reference. The candidate runs with dateutil blocked
and must match it on probe-owned inputs: valid IANA names, unknown names, a malformed key (dateutil
returns None, zoneinfo raises ValueError) and the empty name, naive and offset timestamps, and
invalid timestamps (same exception type). The dependency must leave requirements.txt.
"""

import ast
import os
import sys
import time
from pathlib import Path

os.environ["TZ"] = "UTC"
time.tzset()

from dateutil import parser as du_parser
from dateutil import tz as du_tz

from oracle_protocol import candidate_call


def original_localize(timestamp, zone_name):
    zone = du_tz.gettz(zone_name) or du_tz.UTC
    moment = du_parser.isoparse(timestamp)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=du_tz.UTC)
    return moment.astimezone(zone)


def original_describe(timestamp, zone_name):
    return original_localize(timestamp, zone_name).strftime("%Y-%m-%d %H:%M %Z")


ZONES = ["America/New_York", "Europe/London", "Asia/Kolkata", "UTC", "Etc/GMT+5",
         "Not/AZone", "nonsense", "america/new_york", "Europe/London ", "../etc/passwd", ""]
STAMPS = ["2024-03-10T06:30:00Z", "2024-03-10T06:30:00", "2024-11-03T05:30:00+00:00",
          "2024-07-01T12:00:00.123456+05:30", "2024-07-01", "20240701T120000Z", "2024-07-01T12:00:00+0530"]
INVALID = ("not a date", "2024-02-30")


def fingerprint(moment):
    # Instant, offset, name and wall clock: aware datetimes in a DST fold never compare equal across
    # tzinfo implementations (PEP 495), so `==` would reject a correct result.
    return moment.timestamp(), moment.utcoffset(), moment.tzname(), moment.replace(tzinfo=None)


def raised(function, *args):
    try:
        function(*args)
    except Exception as exc:
        return type(exc)
    return None


# dateutil imports parts of itself lazily, so every reference value is computed before it is blocked.
reference = {(stamp, zone): (fingerprint(original_localize(stamp, zone)), original_describe(stamp, zone))
             for zone in ZONES for stamp in STAMPS}
reference_errors = {stamp: raised(original_localize, stamp, "UTC") for stamp in INVALID}
assert all(reference_errors.values()), "the reference accepts an invalid timestamp"

for name in [module for module in sys.modules if module == "dateutil" or module.startswith("dateutil.")]:
    del sys.modules[name]
for name in ("dateutil", "dateutil.parser", "dateutil.tz", "dateutil.zoneinfo"):
    sys.modules[name] = None
sys.path.insert(0, str(Path.cwd()))
import schedule.tz as candidate

for (stamp, zone), (expected, expected_text) in reference.items():
    actual = candidate_call(candidate.localize, stamp, zone)
    assert fingerprint(actual) == expected, f"localize({stamp!r}, {zone!r}) = {actual!r}, expected {expected!r}"
    actual_text = candidate_call(candidate.describe, stamp, zone)
    assert actual_text == expected_text, f"describe({stamp!r}, {zone!r}) = {actual_text!r}, expected {expected_text!r}"
for stamp, expected_type in reference_errors.items():
    try:
        candidate_call(candidate.localize, stamp, "UTC")
    except expected_type:
        pass
    except Exception as exc:
        raise AssertionError(f"localize({stamp!r}) raised {type(exc).__name__}, expected {expected_type.__name__}") from None
    else:
        raise AssertionError(f"localize({stamp!r}) accepted an invalid timestamp")

requirements = Path("requirements.txt")
if requirements.exists():
    assert "dateutil" not in requirements.read_text(encoding="utf-8").lower(), "python-dateutil is still required"
for source in Path("schedule").rglob("*.py"):
    for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
        names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else (
            [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
        assert not any(name.split(".")[0] == "dateutil" for name in names), f"{source} still imports dateutil"
print("tz replacement: PASS")
