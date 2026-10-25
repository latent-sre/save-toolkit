"""Outcome checks for build-python-engineering-tooling-gap.

CI must run a linter that catches undefined names, with no duplicate linter toolchain. The refund
error path must raise RefundError (not NameError), the candidate's tests must catch the original
NameError defect, and an independent Pyflakes-rule pass over the package must be clean.
"""

import io
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

from oracle_protocol import candidate_call

sys.path.insert(0, str(Path.cwd()))

workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
runs = [str(step.get("run", "")) for job in workflow["jobs"].values() for step in job.get("steps", [])]
assert any(re.search(r"\bruff\b\S*\s+(\S+\s+)*?check\b", run) for run in runs), f"CI runs no lint step: {runs}"
duplicates = [name for name in (".flake8", ".pylintrc", "pylintrc", "tox.ini") if Path(name).exists()]
assert not duplicates and not any("flake8" in run or "pylint" in run for run in runs), \
    f"a second lint toolchain was added: {duplicates or runs}"

ruff = shutil.which("ruff")
command = [ruff] if ruff else [sys.executable, "-m", "ruff"]
result = subprocess.run([*command, "check", "--isolated", "--ignore-noqa", "--select", "F", "payouts"],
                        capture_output=True, text=True, encoding="utf-8", timeout=120)
assert result.returncode == 0, f"Pyflakes rules still fire: {result.stdout[-600:]}"

import payouts.refunds as refunds

try:
    candidate_call(refunds.refund, {"id": "p-1", "amount": 50, "currency": "USD"}, 80)
except refunds.RefundError:
    pass
except Exception as exc:
    raise AssertionError(f"over-refund raised {type(exc).__name__}, expected RefundError") from None
else:
    raise AssertionError("over-refund did not raise")
assert candidate_call(refunds.refund, {"id": "p-2", "amount": 50, "currency": "USD"}, 20) == {
    "payment": "p-2", "amount": 20, "currency": "USD"}, "valid refund changed"

ORIGINAL_ERROR_PATH = '''
def refund(payment, amount):
    if amount > payment["amount"]:
        raise RefundError(f"refund {amount} exceeds payment {payment['id']} of {paymnet['amount']}")
    return {"payment": payment["id"], "amount": amount, "currency": payment["currency"]}
'''
namespace = {"RefundError": refunds.RefundError}
exec(compile(ORIGINAL_ERROR_PATH, "<original>", "exec"), namespace)
refunds.refund = namespace["refund"]
import payouts

if hasattr(payouts, "refund"):
    payouts.refund = namespace["refund"]
suite = unittest.defaultTestLoader.discover("tests", top_level_dir=".")
outcome = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
assert outcome.testsRun and not outcome.wasSuccessful(), "the tests do not catch the original error-path defect"
print("lint gap: PASS")
