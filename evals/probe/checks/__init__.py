"""The checks a build scenario grades, one module per domain, each check declared with what it
asserts, what it reads, and whether it is a check or a probe (see `registry`). Importing the package
registers every declaration; `checking` keeps every name importable under its historical module."""

from __future__ import annotations

from . import changes, checkout, graders, registry, services, state, text, trace  # noqa: F401  # importing registers
from .registry import CHECKS, Kind

# The checks a regrade re-measures with default parameters, as the hand-kept set of earlier runners named them.
REGRADABLE = frozenset(name for name, c in CHECKS.items() if c.can_regrade({"check": name}, {}))
# The probes: what runs once, at trial time, because it reads what leaves with the run.
PROBES = frozenset(name for name, c in CHECKS.items() if c.kind_of({"check": name}, {}) is Kind.PROBE)
