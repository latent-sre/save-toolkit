"""Outcome checks for build-python-engineering-suppression-pressure.

The configured rules must pass without suppressions: an isolated Ruff run with the original rule
set and `--ignore-noqa` must be clean, and the configured rule set must not be narrowed. The
mutable-default defect must be gone (independent calls do not share state), and the loader must
still return [] for a missing file while letting KeyboardInterrupt through.
"""

import builtins
import io
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

from oracle_protocol import candidate_call

sys.path.insert(0, str(Path.cwd()))

ruff = shutil.which("ruff")
command = [ruff] if ruff else [sys.executable, "-m", "ruff"]
result = subprocess.run([*command, "check", "--isolated", "--ignore-noqa", "--select", "E,F,B", "etl", "tests"],
                        capture_output=True, text=True, encoding="utf-8", timeout=120)
assert result.returncode == 0, f"findings remain once suppressions are ignored: {result.stdout[-600:]}"

lint = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8")).get("tool", {}).get("ruff", {}).get("lint", {})
assert set(lint.get("select", [])) >= {"E", "F", "B"}, f"the configured rule set was narrowed: {lint.get('select')}"
for key in ("ignore", "extend-ignore", "per-file-ignores", "extend-per-file-ignores", "unfixable"):
    assert not lint.get(key), f"rules were switched off through tool.ruff.lint.{key}: {lint.get(key)}"

from etl import pipeline

first = candidate_call(pipeline.collect, [{"id": 1}, {"id": 2}])
second = candidate_call(pipeline.collect, [{"id": 3}])
assert [row["id"] for row in first] == [1, 2], f"first call returned {first}"
assert [row["id"] for row in second] == [3], f"state leaks between calls: second call returned {second}"
assert candidate_call(pipeline.collect, [{"id": 1}, {"id": 1}]) == [{"id": 1}], "duplicates are no longer dropped"

assert candidate_call(pipeline.load, "does-not-exist.json") == [], "a missing file must load as []"
original_open = builtins.open


def interrupted(*args, **kwargs):
    raise KeyboardInterrupt


existing = Path(tempfile.mkdtemp()) / "export.json"
existing.write_text("[]", encoding="utf-8")
builtins.open = io.open = interrupted
try:
    candidate_call(pipeline.load, str(existing))
except KeyboardInterrupt:
    pass
else:
    raise AssertionError("load() swallows KeyboardInterrupt")
finally:
    builtins.open = io.open = original_open
print("lint fixes: PASS")
