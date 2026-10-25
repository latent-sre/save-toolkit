"""Outcome checks for build-python-engineering-move-public-symbol.

The money functions move to ledger/money.py as the single implementation. Every published path
keeps working: `ledger.format_amount`, `ledger.helpers.format_amount` (a warning is allowed), the
`ledger.formatters` entry point and the ledger.toml dotted path as resolved by ledger.plugins, and
the old dotted string. Internal modules stop importing the money functions from helpers. Each
import order works in a fresh process, and the unrelated helpers stay where they are.
"""

import ast
import subprocess
import sys
import tomllib
import warnings
from decimal import Decimal
from pathlib import Path

from oracle_protocol import candidate_call

sys.path.insert(0, str(Path.cwd()))

for module in ("ledger", "ledger.money", "ledger.helpers", "ledger.plugins", "ledger.report", "ledger.core"):
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-W", "ignore", "-c", f"import sys; sys.path.insert(0, '.'); import {module}"],
        capture_output=True, text=True, encoding="utf-8", timeout=60,
    )
    assert result.returncode == 0, f"fresh `import {module}` failed: {result.stderr.strip()[-400:]}"

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    import ledger
    import ledger.helpers
    import ledger.money
    import ledger.plugins
    from ledger.core import Ledger


def behaves(format_amount, parse_amount, where):
    assert candidate_call(format_amount, Decimal("1234.5")) == "1,234.50", f"{where}: format_amount changed"
    assert candidate_call(format_amount, Decimal("-0.005")) == "-0.01", f"{where}: rounding changed"
    assert candidate_call(parse_amount, " 1,234.50 ") == Decimal("1234.50"), f"{where}: parse_amount changed"
    try:
        candidate_call(parse_amount, "12.3.4")
    except ValueError:
        pass
    else:
        raise AssertionError(f"{where}: parse_amount accepts malformed input")


behaves(ledger.money.format_amount, ledger.money.parse_amount, "ledger.money")
behaves(ledger.format_amount, ledger.parse_amount, "ledger")
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    behaves(ledger.helpers.format_amount, ledger.helpers.parse_amount, "ledger.helpers")
assert {"format_amount", "parse_amount", "Ledger"} <= set(ledger.__all__), "ledger.__all__ lost public names"
assert callable(ledger.helpers.chunked) and callable(ledger.helpers.slugify), "unrelated helpers moved"

for where, spec in (
    ("the previous dotted path", "ledger.helpers:format_amount"),
    ("ledger.toml", tomllib.loads(Path("ledger.toml").read_text(encoding="utf-8"))["formatter"]),
    ("the entry point", tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
        ["project"]["entry-points"]["ledger.formatters"]["plain"]),
):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        resolved = candidate_call(ledger.plugins.resolve, spec)
    assert candidate_call(resolved, Decimal("7")) == "7.00", f"{where} ({spec}) no longer resolves to the formatter"
assert candidate_call(Ledger().add("3.5").add("1,000").total) == "1,003.50", "Ledger behavior changed"

money_source = Path("ledger/money.py").read_text(encoding="utf-8")
helpers_source = Path("ledger/helpers.py").read_text(encoding="utf-8")
assert "ROUND_HALF_UP" in money_source, "ledger/money.py does not hold the implementation"
assert "ROUND_HALF_UP" not in helpers_source, "helpers.py still carries a second implementation"

for name in ("core.py", "report.py", "plugins.py"):
    tree = ast.parse(Path("ledger", name).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("helpers"):
            moved = {alias.name for alias in node.names} & {"format_amount", "parse_amount"}
            assert not moved, f"ledger/{name} still imports {sorted(moved)} from helpers"
        if isinstance(node, ast.Attribute) and node.attr in ("format_amount", "parse_amount"):
            assert not (isinstance(node.value, ast.Name) and node.value.id == "helpers"), \
                f"ledger/{name} still calls helpers.{node.attr}"
        if isinstance(node, ast.Constant) and node.value == "ledger.helpers:format_amount":
            raise AssertionError(f"ledger/{name} still registers the old dotted path")
print("money move: PASS")
